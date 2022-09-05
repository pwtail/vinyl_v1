# pragma: i/o specific
from contextlib import contextmanager
from contextvars import ContextVar

from django.db import DEFAULT_DB_ALIAS

from vinyl.patches import orig


@contextmanager
def no_op():
    yield


class AsyncBackend:
    def __init__(self, settings_dict, alias=DEFAULT_DB_ALIAS):
        super().__init__(settings_dict, alias)
        self.connection = ContextVar('async_connection', default=None)

    @contextmanager
    def set_connection(self, conn):
        _token = self.connection.set(conn)
        try:
            yield
        finally:
            self.connection.set(None)

    def get_connection(self):
        return self.connection.get()


class SyncBackend:

    @contextmanager
    def set_connection(self, conn):
        self.connection = conn
        try:
            yield
        finally:
            self.connection = None

    def get_connection(self):
        return self.connection

    def transaction(self):
        return orig.Atomic(self.alias, savepoint=True, durable=False)