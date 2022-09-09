# pragma: i/o specific

import psycopg_pool

from vinyl.backends.backend_impl import SyncBackend
from vinyl.backends.postgresql.common import PgBackend


class DatabaseWrapper(SyncBackend, PgBackend):

    def make_pool(self, dsn):
        return psycopg_pool.ConnectionPool(dsn,
                                           min_size=1, max_size=1, timeout=1,
                                           configure=self.configure_connection)
