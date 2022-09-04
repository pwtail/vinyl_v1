import psycopg_pool
from django.db.backends.postgresql.base import DatabaseWrapper as _DatabaseWrapper

from vinyl.backend_impl import SyncBackend
from postgresql_backend.common import PgBackend


class DatabaseWrapper(SyncBackend, PgBackend, _DatabaseWrapper):

    def make_pool(self, dsn):
        return psycopg_pool.ConnectionPool(dsn, max_size=1,
                                           configure=self.configure_connection)
