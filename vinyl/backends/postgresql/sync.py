# pragma: i/o specific

import psycopg_pool
from django.db.backends.postgresql.base import DatabaseWrapper as _DatabaseWrapper

from vinyl.backends.backend_impl import SyncBackend
from vinyl.backends.postgresql.common import PgBackend
from vinyl.backends.postgresql.restrictions import Restrictions


class DatabaseWrapper(Restrictions, SyncBackend, PgBackend, _DatabaseWrapper):

    def make_pool(self, dsn):
        return psycopg_pool.ConnectionPool(dsn,
                                           min_size=1, max_size=1, timeout=1,
                                           configure=self.configure_connection)
