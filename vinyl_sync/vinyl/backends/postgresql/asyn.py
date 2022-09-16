# pragma: i/o specific
import psycopg_pool
from django.db.backends.postgresql.base import DatabaseWrapper as _DatabaseWrapper

from vinyl.backends.backend_impl import AsyncBackend
from vinyl.backends.postgresql.common import PgBackend
from vinyl.backends.postgresql.restrictions import Restrictions


class DatabaseWrapper(Restrictions, AsyncBackend, PgBackend, _DatabaseWrapper):

    def make_pool(self, dsn):
        return psycopg_pool.AsyncConnectionPool(dsn, configure=self.configure_connection)
