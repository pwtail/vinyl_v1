from contextlib import contextmanager
from itertools import chain

from django.db import NotSupportedError, connections
from django.db.models import QuerySet, Model, Count
from django.db.models.query import MAX_GET_RESULTS
from django.db.models.sql import Query
from django.db.models.sql.constants import SINGLE, MULTI

from vinyl import deferred
from vinyl.pre_evaluation import QueryResult
from vinyl.prefetch import prefetch_related_objects


class VinylQuerySet(QuerySet):


    # almost exact copy, except for the await statement
    async def get(self, *args, **kwargs):
        if self.query.combinator and (args or kwargs):
            raise NotSupportedError(
                "Calling QuerySet.get(...) with filters after %s() is not "
                "supported." % self.query.combinator
            )
        clone = self._chain() if self.query.combinator else self.filter(*args, **kwargs)
        if self.query.can_filter() and not self.query.distinct_fields:
            clone = clone.order_by()
        limit = None
        if (
            not clone.query.select_for_update
            or connections[clone.db].features.supports_select_for_update_with_limit
        ):
            limit = MAX_GET_RESULTS
            clone.query.set_limits(high=limit)
        await clone
        num = len(clone)
        if num == 1:
            return clone._result_cache[0]
        if not num:
            raise self.model.DoesNotExist(
                "%s matching query does not exist." % self.model._meta.object_name
            )
        raise self.model.MultipleObjectsReturned(
            "get() returned more than one %s -- it returned %s!"
            % (
                self.model._meta.object_name,
                num if not limit or num < limit else "more than %s" % (limit - 1),
            )
        )


    @classmethod
    def clone(cls, qs):
        query = VinylQuery.convert(qs.query)
        c = cls(
            model=query.model,
            query=query,
            using=qs._db,
            hints=qs._hints,
        )
        c._sticky_filter = qs._sticky_filter
        c._for_write = qs._for_write
        c._prefetch_related_lookups = qs._prefetch_related_lookups[:]
        c._known_related_objects = qs._known_related_objects
        c._iterable_class = qs._iterable_class
        c._fields = qs._fields
        return c

    def __init__(self, model=None, query=None, using=None, hints=None):
        assert model

        # query = VinylQuery.convert(query)
        from vinyl.model import VinylModel
        if not issubclass(model, VinylModel):
            assert issubclass(model, Model)
            model = model.vinyl_model
        query = query or VinylQuery(model)
        super().__init__(model=model, query=query, using=using, hints=hints)


    def __await__(self):
        return self._await().__await__()

    async def _await(self):
        compiler = self.query.get_compiler(using=self.db)
        await compiler
        self._fetch_all()
        if self._prefetch_related_lookups and not self._prefetch_done:
            await self._prefetch_related_objects()
        return self._result_cache

    def _fetch_all(self):
        if self._result_cache is None:
            self._result_cache = list(self._iterable_class(self))
        # no prefetch related

    async def _prefetch_related_objects(self):
        await prefetch_related_objects(self._result_cache, *self._prefetch_related_lookups)
        self._prefetch_done = True

    def prefetch(self, *args, **kw):
        return self.prefetch_related(*args, **kw)

    @property
    def db(self):
        db = super().db
        if db.startswith('vinyl_'):
            return db
        return f'vinyl_{db}'

    async def get_or_none(self):
        try:
            return await self.get()
        except self.model.DoesNotExist:
            return None

    async def delete(self):
        await self
        async with deferred.driver():
            super().delete()









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