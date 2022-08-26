from contextlib import asynccontextmanager
from contextvars import ContextVar

from django.core.exceptions import ImproperlyConfigured
from django.db.backends.postgresql.base import DatabaseWrapper as _DatabaseWrapper

from vinyl.postgresql_backend.ops import DatabaseOperations

import psycopg
import psycopg_pool

class DatabaseWrapper(_DatabaseWrapper):
    ops_class = DatabaseOperations

    async_pool = None
    async_connection = ContextVar('async_connection', default=None)

    CursorWrapper = None

    async def start_pool(self):
        conn_params = self.get_connection_params()
        dsn = self._to_dsn(**conn_params)
        pool = psycopg_pool.AsyncConnectionPool(dsn, open=False, configure=self.configure_connection)
        await pool.open()
        self.async_pool = pool  # TODO contextvar like connection ?
        return pool

    async def execute_sql(self, sql, params):
        """
        Execute and fetch multiple rows
        """
        async with self.cursor() as cursor:
            await cursor.execute(sql, params)
            results = await cursor.fetchall()
            return (results,)  # FIXME

    def _to_dsn(self, **kwargs):
        kwargs['dbname'] = kwargs.pop('database')
        del kwargs['password']  # wtf?
        return ' '.join(f'{k}={v}' for k, v in kwargs.items())

    async def configure_connection(self, connection):
        options = self.settings_dict['OPTIONS']
        try:
            isolevel = options['isolation_level']
        except KeyError:
            self.isolation_level = None
        else:
            try:
                self.isolation_level = self.Database.IsolationLevel(isolevel)
            except ValueError:
                raise ImproperlyConfigured(
                    "bad isolation_level: %s. Choose one of the 'psycopg.IsolationLevel' values" %
                    (options['isolation_level'],))
            connection.isolation_level = self.isolation_level

    @asynccontextmanager
    async def cursor(self):
        # if self.async_pool is None:
        #     await self.start_pool()
        if (conn := self.async_connection.get()) is not None:
            async with conn.cursor() as cur:
                if self.CursorWrapper:
                    cur = self.CursorWrapper(cur)
                yield cur
            return
        async with self.get_connection_from_pool() as conn:
            token = self.async_connection.set(conn)
            try:
                async with conn.cursor() as cur:
                    if self.CursorWrapper:
                        cur = self.CursorWrapper(cur)
                    yield cur
            finally:
                self.async_connection.reset(token)

    @asynccontextmanager
    async def get_connection_from_pool(self):
        if self.async_pool is None:
            await self.start_pool()
        async with self.async_pool.connection() as conn:
            yield conn

    def transaction(self):
        if self.async_connection.get():
            return no_op()
        return self.get_connection_from_pool()

    async def execute_only(self, sql, params):
        """
        Execute but do not fetch
        """
        async with self.cursor() as cursor:
            await cursor.execute(sql, params)