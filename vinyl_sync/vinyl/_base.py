from functools import cached_property

import django.db.backends.postgresql.base
import psycopg_pool

from vinyl.backends.backend_impl import SyncBackend
from vinyl.backends.postgresql.common import PgBackend
from vinyl.backends.postgresql.ops import DatabaseOperations


class DatabaseWrapper(SyncBackend, PgBackend):
    ops_class = DatabaseOperations
    fallback_class = django.db.backends.postgresql.base.DatabaseWrapper


    @cached_property
    def ops(self):
        return self.ops_class(self)

    def __init__(self, *args, **kw):
        self._fallback = self.fallback_class(*args, **kw)

    def __getattr__(self, name):
        return getattr(self._fallback, name)

    def make_pool(self, dsn):
        return psycopg_pool.ConnectionPool(dsn,
                                           min_size=1, max_size=1, timeout=1,
                                           configure=self.configure_connection)