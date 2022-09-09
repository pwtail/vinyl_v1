# pragma: i/o specific

from django.db.backends.mysql.base import DatabaseWrapper as _DatabaseWrapper

from vinyl.backends.backend import Backend
from vinyl.backends.backend_impl import SyncBackend
from vinyl.backends.mysql.ops import DatabaseOperations
from vinyl.patches import orig


class DatabaseWrapper(SyncBackend, Backend, _DatabaseWrapper):
    ops_class = DatabaseOperations

    def transaction(self):
        return orig.Atomic(self.alias, savepoint=True, durable=False)