from django.db import connections
from django.db.models.sql import compiler as _compiler
from django.db.models.sql.compiler import *

from vinyl.deferred import statements


class StatementsMixin:
    def add_statement(self, *stmt):
        items = statements.get()
        if not items:
            items.using = self.using
        else:
            assert items.using == self.using
        items.append(stmt)


class ExecuteMixin(StatementsMixin, _compiler.SQLCompiler):

    results = None

    def __await__(self):
        return self._await().__await__()

    async def has_results(self):
        results = await self.async_execute_sql()
        # results = tuple(chain.from_iterable(results))
        return bool(results[0])

    async def _await(self):
        self.results = await self.async_execute_sql()
        self.query.get_compiler = lambda *args, **kw: self
        # self.query.pre_evaluated = QueryResult(compiler=self, results=results)
        return self.results

    # def execute_multi

    async def explain_query(self):
        result = list(await self.async_execute_sql())
        # Some backends return 1 item tuples with strings, and others return
        # tuples with integers and strings. Flatten them out into strings.
        format_ = self.query.explain_info.format
        output_formatter = json.dumps if format_ and format_.lower() == "json" else str
        rows = []
        for row in result[0]:
            if not isinstance(row, str):
                rows.append(" ".join(output_formatter(c) for c in row))
            else:
                rows.append(row)
        #TODO pprint
        return '\n'.join(rows)

    def execute_sql(self, result_type=MULTI, **kw):
        if self.results is not None:
            return self.results
            # TODO del for assertion
        sql, params = self.as_sql()
        self.add_statement(sql, params)

    async def async_execute_sql(self, result_type=MULTI):
        assert result_type == MULTI
        try:
            sql, params = self.as_sql()
            if not sql:
                raise EmptyResultSet
        except EmptyResultSet:
            return iter([])
        return await connections[self.using].execute_sql(sql, params)
        #
        #
        # #TODO use pool
        # import psycopg
        # async with await psycopg.AsyncConnection.connect(
        #         "dbname=lulka user=postgres"
        # ) as aconn:
        #     async with aconn.cursor() as cursor:
        #         await cursor.execute(sql, params)
        #         if result_type == SINGLE:
        #             val = await cursor.fetchone()
        #             if val:
        #                 return val[0:self.col_count]
        #             return val
        #         elif result_type == MULTI:
        #             results = await cursor.fetchall()
        #             return (results,)
        #         elif result_type == CURSOR:
        #             assert False
        #             return RetCursor(cursor.rowcount, getattr(cursor, 'lastrowid', None))


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

class DeferredCompilerMixin(StatementsMixin):
    def execute_sql(self, result_type, **kw):
        try:
            sql, params = self.as_sql()
        except EmptyResultSet:
            return
        self.add_statement(sql, params)


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

        async with connections[self.using].cursor() as cursor:
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
            self.add_statement(sql, params)

    @property
    def execute_sql(self):
        if statements.get(None) is not None:
            return self.sync_execute_sql
        return self.async_execute_sql


class SQLDeleteCompiler(DeferredCompilerMixin, _compiler.SQLDeleteCompiler):

    def execute_sql(self, result_type, **kw):
        sql, params = self.as_sql()
        self.add_statement(sql, params)
