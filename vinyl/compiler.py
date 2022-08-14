import typing

from django.db import connections
from django.db.models.sql import compiler as _compiler

from django.db.models.sql.compiler import *

from vinyl.pre_evaluation import QuerySetResult


class ExecuteMixin:

    def execute_sql(self, result_type=MULTI, **kw):
        if result := QuerySetResult.get():
            return result.results
        if tl := getattr(tlocal, 'deferred', None):
            sql, params = self.as_sql()
            tl.setdefault('ops', []).append((sql, params))
            return
        assert False
        return super().execute_sql(result_type=result_type)

    async def async_execute_sql(self, result_type=MULTI):
        assert result_type == MULTI
        # result_type = result_type or NO_RESULTS
        try:
            sql, params = self.as_sql()
            if not sql:
                raise EmptyResultSet
        except EmptyResultSet:
            if result_type == MULTI:
                return iter([])
            else:
                return None
        #TODO use pool
        import psycopg
        async with await psycopg.AsyncConnection.connect(
                "dbname=lulka user=postgres"
        ) as aconn:
            async with aconn.cursor() as cursor:
                await cursor.execute(sql, params)
                if result_type == SINGLE:
                    val = await cursor.fetchone()
                    if val:
                        return val[0:self.col_count]
                    return val
                elif result_type == MULTI:
                    results = await cursor.fetchall()
                    return (results,)
                elif result_type == CURSOR:
                    return RetCursor(cursor.rowcount, getattr(cursor, 'lastrowid', None))


class SQLCompiler(ExecuteMixin, _compiler.SQLCompiler):
    #
    # def results_iter(
    #     self,
    #     results=None,
    #     tuple_expected=False,
    #     chunked_fetch=False,
    #     chunk_size=GET_ITERATOR_CHUNK_SIZE,
    # ):
    #     """Return an iterator over the results from executing this query."""
    #     assert results is not None
    #     #TODO or tl
    #     return super().results_iter(results=results, tuple_expected=tuple_expected)
    #
    1

class DeferredCompilerMixin:
    def execute_sql(self, result_type, **kw):
        print(result_type)
        # async ctx mgr
        ct = get_ctx()


class RetCursor(typing.NamedTuple):
    """
    An object to return when result_type is CURSOR
    """
    rowcount: int
    lastrowid: object

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def close(self):
        pass



class SQLUpdateCompiler(DeferredCompilerMixin, _compiler.SQLUpdateCompiler):

    def execute_sql(self, result_type=MULTI, **kw):
        1