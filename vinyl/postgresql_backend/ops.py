# pragma: i/o specific

from django.db.backends.postgresql.operations import DatabaseOperations as _DatabaseOperations


class DatabaseOperations(_DatabaseOperations):
    compiler_module = "vinyl.compiler"