import typing

from django.db import connections
from django.db.models.sql import compiler as _compiler

from django.db.models.sql.compiler import *

from vinyl.tlocal import tlocal


class ExecuteMixin:

    def execute_sql(self, result_type=MULTI):
        if tl := getattr(tlocal, 'await_queryset', None):
            return tl['execute_sql']
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
                    return await cursor.fetchall()
                elif result_type == CURSOR:
                    return RetCursor(cursor.rowcount, getattr(cursor, 'lastrowid', None))


class SQLCompiler(ExecuteMixin, _compiler.SQLCompiler):

    def results_iter(
        self,
        results=None,
        tuple_expected=False,
        chunked_fetch=False,
        chunk_size=GET_ITERATOR_CHUNK_SIZE,
    ):
        """Return an iterator over the results from executing this query."""
        assert results is not None
        #TODO or tl
        return ...

    def convert_rows(self, rows, tuple_expected=False):
        "Apply converters."
        fields = [s[0] for s in self.select[0 : self.col_count]]
        converters = self.get_converters(fields)
        if converters:
            rows = self.apply_converters(rows, converters)
            if tuple_expected:
                rows = map(tuple, rows)
        return rows

    def has_results(self):
        """
        Backends (e.g. NoSQL) can override this in order to use optimized
        versions of "query has any results."
        """
        result = self.execute_sql(SINGLE)

        @later
        def ret(result=result):
            return bool(result)
        return ret()



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

