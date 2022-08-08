from django.db.models import QuerySet
from django.db.models.sql import Query

from vinyl.tlocal import tlocal_context, tlocal


class VinylQuerySet(QuerySet):

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
        return self._result_cache


class VinylQuery(Query):

    def get_compiler(self, using=None, connection=None, elide_empty=True):
        if tl := getattr(tlocal, 'await_queryset', None):
            return tl['compiler']
        return super().get_compiler(using=using, connection=connection, elide_empty=elide_empty)