# pragma: i/o specific

from django.db.backends.mysql.base import DatabaseWrapper as _DatabaseWrapper

from vinyl.backend import Backend
from vinyl.backend_impl import SyncBackend

from vinyl.mariadb_backend.ops import DatabaseOperations


class DatabaseWrapper(SyncBackend, Backend, _DatabaseWrapper):
    ops_class = DatabaseOperations

