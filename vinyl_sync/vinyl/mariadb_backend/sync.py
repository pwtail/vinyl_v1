# pragma: i/o specific

from django.db.backends.mysql.base import DatabaseWrapper as _DatabaseWrapper

from vinyl.backend_impl import SyncBackend

from vinyl.mariadb_backend.ops import DatabaseOperations
from vinyl.patches import orig


class DatabaseWrapper(SyncBackend, _DatabaseWrapper):
    ops_class = DatabaseOperations

    def transaction(self):
        return orig.Atomic(self.alias, savepoint=True, durable=False)