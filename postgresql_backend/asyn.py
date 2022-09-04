import psycopg_pool
from django.db.backends.postgresql.base import DatabaseWrapper as _DatabaseWrapper

from vinyl.backend_impl import AsyncBackend
from postgresql_backend.common import PgBackend


class DatabaseWrapper(AsyncBackend, PgBackend, _DatabaseWrapper):

    def make_pool(self, dsn):
        return psycopg_pool.AsyncConnectionPool(dsn, configure=self.configure_connection)
