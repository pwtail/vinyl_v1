from django.db.backends.mysql.operations import DatabaseOperations as _DatabaseOperations


class DatabaseOperations(_DatabaseOperations):
    compiler_module = "vinyl.compiler"