from itertools import chain

from django.db import connections
from django.db.models import Model, Count, Value
from django.db.models.sql import Query
from django.db.models.sql.constants import MULTI
from django.db.models.sql.query import EXPLAIN_OPTIONS_PATTERN, ExplainInfo


class VinylQuery(Query):

    pre_evaluated = None

    @classmethod
    def convert(cls, query):
        if isinstance(query, VinylQuery):
            return query
        query = query.chain(klass=cls)
        from vinyl.model import VinylModel
        if not issubclass(query.model, VinylModel):
            assert issubclass(query.model, Model)
            query.model = query.model.vinyl_model
        return query

    def get_compiler(self, using=None, connection=None, elide_empty=True):
        if pre := self.pre_evaluated:
            return pre.compiler
        return super().get_compiler(using=using, connection=connection, elide_empty=elide_empty)

    async def get_aggregation(self, using, added_aggregate_names):
        """
        Return the dictionary with the values of the existing aggregations.
        """
        if not self.annotation_select:
            return {}
        existing_annotations = [
            annotation
            for alias, annotation in self.annotations.items()
            if alias not in added_aggregate_names
        ]
        # Decide if we need to use a subquery.
        #
        # Existing annotations would cause incorrect results as get_aggregation()
        # must produce just one result and thus must not use GROUP BY. But we
        # aren't smart enough to remove the existing annotations from the
        # query, so those would force us to use GROUP BY.
        #
        # If the query has limit or distinct, or uses set operations, then
        # those operations must be done in a subquery so that the query
        # aggregates on the limit and/or distinct results instead of applying
        # the distinct and limit after the aggregation.
        if (
            isinstance(self.group_by, tuple)
            or self.is_sliced
            or existing_annotations
            or self.distinct
            or self.combinator
        ):
            from django.db.models.sql.subqueries import AggregateQuery

            inner_query = self.clone()
            inner_query.subquery = True
            outer_query = AggregateQuery(self.model, inner_query)
            inner_query.select_for_update = False
            inner_query.select_related = False
            inner_query.set_annotation_mask(self.annotation_select)
            # Queries with distinct_fields need ordering and when a limit is
            # applied we must take the slice from the ordered query. Otherwise
            # no need for ordering.
            inner_query.clear_ordering(force=False)
            if not inner_query.distinct:
                # If the inner query uses default select and it has some
                # aggregate annotations, then we must make sure the inner
                # query is grouped by the main model's primary key. However,
                # clearing the select clause can alter results if distinct is
                # used.
                has_existing_aggregate_annotations = any(
                    annotation
                    for annotation in existing_annotations
                    if getattr(annotation, "contains_aggregate", True)
                )
                if inner_query.default_cols and has_existing_aggregate_annotations:
                    inner_query.group_by = (
                        self.model._meta.pk.get_col(inner_query.get_initial_alias()),
                    )
                inner_query.default_cols = False

            relabels = {t: "subquery" for t in inner_query.alias_map}
            relabels[None] = "subquery"
            # Remove any aggregates marked for reduction from the subquery
            # and move them to the outer AggregateQuery.
            col_cnt = 0
            for alias, expression in list(inner_query.annotation_select.items()):
                annotation_select_mask = inner_query.annotation_select_mask
                if expression.is_summary:
                    expression, col_cnt = inner_query.rewrite_cols(expression, col_cnt)
                    outer_query.annotations[alias] = expression.relabeled_clone(
                        relabels
                    )
                    del inner_query.annotations[alias]
                    annotation_select_mask.remove(alias)
                # Make sure the annotation_select wont use cached results.
                inner_query.set_annotation_mask(inner_query.annotation_select_mask)
            if (
                inner_query.select == ()
                and not inner_query.default_cols
                and not inner_query.annotation_select_mask
            ):
                # In case of Model.objects[0:3].count(), there would be no
                # field selected in the inner query, yet we must use a subquery.
                # So, make sure at least one field is selected.
                inner_query.select = (
                    self.model._meta.pk.get_col(inner_query.get_initial_alias()),
                )
        else:
            outer_query = self
            self.select = ()
            self.default_cols = False
            self.extra = {}

        empty_set_result = [
            expression.empty_result_set_value
            for expression in outer_query.annotation_select.values()
        ]
        elide_empty = not any(result is NotImplemented for result in empty_set_result)
        outer_query.clear_ordering(force=True)
        outer_query.clear_limits()
        outer_query.select_for_update = False
        outer_query.select_related = False
        compiler = outer_query.get_compiler(using, elide_empty=elide_empty)
        await compiler
        # result = compiler.execute_sql(SINGLE)
        results = compiler.execute_sql(MULTI)
        rows = chain.from_iterable(results)
        # if result is None:
        #     result = empty_set_result

        converters = compiler.get_converters(outer_query.annotation_select.values())
        result = next(compiler.apply_converters(rows, converters))

        return dict(zip(outer_query.annotation_select, result))

    async def get_count(self, using):
        """
        Perform a COUNT() query using the current filter constraints.
        """
        obj = self.clone()
        obj.add_annotation(Count("*"), alias="__count", is_summary=True)
        result = await obj.get_aggregation(using, ["__count"])
        return result["__count"]

    def explain(self, using, format=None, **options):
        q = self.clone()
        for option_name in options:
            if (
                    not EXPLAIN_OPTIONS_PATTERN.fullmatch(option_name)
                    or "--" in option_name
            ):
                raise ValueError(f"Invalid option name: {option_name!r}.")
        q.explain_info = ExplainInfo(format, options)
        compiler = q.get_compiler(using=using)
        return compiler.explain_query()