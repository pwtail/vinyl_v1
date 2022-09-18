from django.db import connections
from django.db.models.sql import compiler as _compiler
from django.db.models.sql.compiler import *

from vinyl.deferred import is_collecting_sql, tl


class StatementsMixin:
    def add_statement(self, *stmt):
        #FIXME
        assert (items := tl.collected_sql) is not None
        if not items:
            items.using = self.using
        else:
            assert items.using == self.using
        items.append(stmt)


class ExecuteMixin(_compiler.SQLCompiler):

    results = None

    def __await__(self):
        return self.__Await__().__await__()

    async def __Await__(self):
        self.results = await self._execute_sql()
        self.query.get_compiler = lambda *args, **kw: self
        return self.results

    def execute_sql(self, result_type=MULTI, **kw):
        assert self.results is not None
        return self.results

    async def _execute_sql(self, result_type=MULTI):
        assert result_type == MULTI
        try:
            sql, params = self.as_sql()
            if not sql:
                raise EmptyResultSet
        except EmptyResultSet:
            return iter([])
        return await connections[self.using].execute_sql(sql, params)

    async def has_results(self):
        results = await self._execute_sql()
        # results = tuple(chain.from_iterable(results))
        return bool(results[0])

    async def explain_query(self):
        result = list(await self._execute_sql())
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

class SQLCompiler(ExecuteMixin, _compiler.SQLCompiler):
    pass


class DeferredCompilerMixin(StatementsMixin):
    def execute_sql(self, result_type, **kw):
        assert result_type != MULTI
        try:
            sql, params = self.as_sql()
        except EmptyResultSet:
            return
        self.add_statement(sql, params)


class SQLUpdateCompiler(_compiler.SQLUpdateCompiler):
    pass


class SQLInsertCompiler(DeferredCompilerMixin, _compiler.SQLInsertCompiler):

    async def _execute_sql(self, returning_fields=None):
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

    def _defer_execute_sql(self, returning_fields=None):
        assert not returning_fields
        for sql, params in self.as_sql():
            self.add_statement(sql, params)

    @property
    def execute_sql(self):
        if is_collecting_sql():
            return self._defer_execute_sql
        return self._execute_sql


class SQLDeleteCompiler(DeferredCompilerMixin, _compiler.SQLDeleteCompiler):

    def execute_sql(self, result_type, **kw):
        sql, params = self.as_sql()
        self.add_statement(sql, params)
