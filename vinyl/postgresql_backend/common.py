from contextlib import contextmanager, asynccontextmanager

from django.core.exceptions import ImproperlyConfigured

from vinyl.backend import Backend
from vinyl.postgresql_backend.ops import DatabaseOperations


class PgBackend(Backend):
    ops_class = DatabaseOperations

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
        self.pool = pool
        return pool

    @asynccontextmanager
    async def get_connection_from_pool(self):
        if self.pool is None:
            await self.start_pool()
        async with self.pool.connection() as conn:
            yield conn