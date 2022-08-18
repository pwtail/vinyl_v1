import typing

from django.db import connections
from django.db.models.sql import compiler as _compiler

from django.db.models.sql.compiler import *

from vinyl.deferred import add_statement
from vinyl.pre_evaluation import QueryResult


class ExecuteMixin:

    def __await__(self):
        return self._await().__await__()

    async def _await(self):
        results = await self.async_execute_sql()
        self.query.pre_evaluated = QueryResult(compiler=self, results=results)
        return results

    # def execute_multi

    def execute_sql(self, result_type=MULTI, **kw):
        if pre := self.query.pre_evaluated:
            assert pre.compiler is self
            return pre.results
            # TODO del for assertion
        sql, params = self.as_sql()
        add_statement(sql, params)
        # assert False
        # return super().execute_sql(result_type=result_type)

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
        # print(result_type)
        sql, params = self.as_sql()
        add_statement(sql, params)


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
    pass


class SQLInsertCompiler(_compiler.SQLInsertCompiler):

    def execute_sql(self, result_type, **kw):
        for sql, params in self.as_sql():
            add_statement(sql, params)


class SQLDeleteCompiler(_compiler.SQLDeleteCompiler):

    def execute_sql(self, result_type, **kw):
        sql, params = self.as_sql()
        add_statement(sql, params)
