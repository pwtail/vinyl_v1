from django.db.models import QuerySet
from django.db.models.sql import Query

from vinyl.prefetch import prefetch_related_objects
from vinyl.tlocal import tlocal_context, tlocal


class VinylQuerySet(QuerySet):

    @classmethod
    def clone(cls, qs):
        c = cls(
            model=qs.model,
            query=qs.query.chain(klass=VinylQuery),
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
        query = query or VinylQuery(model)
        super().__init__(model=model, query=query, using=using, hints=hints)

    def __await__(self):
        return self._await().__await__()

    async def _await(self):
        db = self.db
        compiler = self.query.get_compiler(using=db)
        results = await compiler.async_execute_sql()
        with tlocal_context('await_queryset') as tl:
            tl['compiler'] = compiler
            tl['execute_sql'] = results
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


class VinylQuery(Query):

    def get_compiler(self, using=None, connection=None, elide_empty=True):
        if tl := getattr(tlocal, 'await_queryset', None):
            return tl['compiler']
        return super().get_compiler(using=using, connection=connection, elide_empty=elide_empty)