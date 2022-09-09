from functools import cached_property

import django.db.backends.postgresql.base
import psycopg_pool

from vinyl.backend_impl import SyncBackend
from vinyl.postgresql_backend.common import PgBackend
from vinyl.postgresql_backend.ops import DatabaseOperations

Fallback = django.db.backends.postgresql.base.DatabaseWrapper

class DatabaseWrapper(SyncBackend, PgBackend):
    ops_class = DatabaseOperations

    @cached_property
    def ops(self):
        return self.ops_class(self)

    def __init__(self, *args, **kw):
        self._fallback = Fallback(*args, **kw)

    def __getattr__(self, name):
        return getattr(self._fallback, name)

    def make_pool(self, dsn):
        return psycopg_pool.ConnectionPool(dsn,
                                           min_size=1, max_size=1, timeout=1,
                                           configure=self.configure_connection)