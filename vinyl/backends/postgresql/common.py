from contextlib import asynccontextmanager
from functools import cached_property

import django.db.backends.postgresql.base
import psycopg
from django.core.exceptions import ImproperlyConfigured

from vinyl.backends.backend import PooledBackend
from vinyl.backends.postgresql.ops import DatabaseOperations


class PgBackend(PooledBackend):
    ops_class = DatabaseOperations
    fallback_class = django.db.backends.postgresql.base.DatabaseWrapper

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

    def make_pool(self, dsn):
        raise NotImplementedError

    async def start_pool(self):
        conn_params = self.get_connection_params()
        dsn = self._to_dsn(**conn_params)
        pool = self.make_pool(dsn)
        await pool.open()
        self.pool = pool
        return pool

    @asynccontextmanager
    async def get_connection_from_pool(self):
        if self.pool is None:
            await self.start_pool()
        async with self.pool.connection() as conn:
            with self.set_connection(conn):
                yield conn

    @cached_property
    def pg_version(self):
        return psycopg.pq.version()

    # @asynccontextmanager
    # def _nodb_cursor(self):
    #     nodb = self.__class__({**self.settings_dict, "NAME": None}, alias=NO_DB_ALIAS)
    #     conn_params = nodb.get_connection_params()
    #     dsn = nodb._to_dsn(**conn_params)
    #     async with psycopg.connect(dsn, autocommit=True) as conn:
    #         async with conn.cursor() as cursor:
    #             yield cursor

    async def close(self):
        if self.pool:
            await self.pool.close()