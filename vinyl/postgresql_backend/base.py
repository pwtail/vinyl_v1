from django.db.backends.postgresql.base import DatabaseWrapper as _DatabaseWrapper

from vinyl.postgresql_backend.ops import DatabaseOperations


class DatabaseWrapper(_DatabaseWrapper):
    ops_class = DatabaseOperations