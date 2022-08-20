import typing

from django.db import connections
from django.db.models.sql import compiler as _compiler

from django.db.models.sql.compiler import *

from vinyl.deferred import add_statement, statements
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
                    assert False
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


#TODO remove
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

    async def async_execute_sql(self, returning_fields=None):
        assert not (
                returning_fields
                and len(self.query.objs) != 1
                and not self.connection.features.can_return_rows_from_bulk_insert
        )
        opts = self.query.get_meta()
        self.returning_fields = returning_fields

        import psycopg
        async with await psycopg.AsyncConnection.connect(
                "dbname=lulka user=postgres"
        ) as aconn:

            async with aconn.cursor() as cursor:
                for sql, params in self.as_sql():
                    await cursor.execute(sql, params)

                if not self.returning_fields:
                    return []
                if (
                        self.connection.features.can_return_rows_from_bulk_insert
                        and len(self.query.objs) > 1
                ):
                    rows = await self.connection.ops.fetch_returned_insert_rows(cursor)
                elif self.connection.features.can_return_columns_from_insert:
                    assert len(self.query.objs) == 1
                    rows = [
                        await self.connection.ops.fetch_returned_insert_columns(
                            cursor,
                            self.returning_params,
                        )
                    ]
                else:
                    rows = [
                        (
                            self.connection.ops.last_insert_id(
                                cursor,
                                opts.db_table,
                                opts.pk.column,
                            ),
                        )
                    ]
        cols = [field.get_col(opts.db_table) for field in self.returning_fields]
        converters = self.get_converters(cols)
        if converters:
            rows = list(self.apply_converters(rows, converters))
        return rows

    def sync_execute_sql(self, returning_fields=None):
        assert not returning_fields
        for sql, params in self.as_sql():
            add_statement(sql, params)

    @property
    def execute_sql(self):
        if statements.get(None) is not None:
            return self.sync_execute_sql
        return self.async_execute_sql


class SQLDeleteCompiler(_compiler.SQLDeleteCompiler):

    def execute_sql(self, result_type, **kw):
        sql, params = self.as_sql()
        add_statement(sql, params)
