from contextlib import contextmanager

from django.db import NotSupportedError, connections
from django.db.models import QuerySet, Model
from django.db.models.query import MAX_GET_RESULTS
from django.db.models.sql import Query

from vinyl.pre_evaluation import pre_evaluate, QuerySetResult
from vinyl.prefetch import prefetch_related_objects


class VinylQuerySet(QuerySet):


    # almost exact copy
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
        db = self.db
        compiler = self.query.get_compiler(using=db)
        results = await compiler.async_execute_sql()
        with pre_evaluate(queryset=self, compiler=compiler, results=results):
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



class VinylQuery(Query):

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
        if result := QuerySetResult.get():
            assert result.qs.query is self
            return result.compiler
        return super().get_compiler(using=using, connection=connection, elide_empty=elide_empty)