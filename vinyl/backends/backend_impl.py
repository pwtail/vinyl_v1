# pragma: i/o specific
from contextlib import contextmanager
from contextvars import ContextVar

from django.db import DEFAULT_DB_ALIAS


@contextmanager
def no_op():
    yield


class AsyncBackend:
    def __init__(self, settings_dict, alias=DEFAULT_DB_ALIAS):
        super().__init__(settings_dict, alias)
        self.conn = ContextVar('async_connection', default=None)

    @contextmanager
    def set_connection(self, conn):
        _token = self.conn.set(conn)
        try:
            yield
        finally:
            self.conn.set(None)

    def get_connection(self):
        return self.conn.get()


# TODO sync conn
class SyncBackend:

    @contextmanager
    def set_connection(self, conn):
        self.conn = conn
        try:
            yield
        finally:
            self.conn = None

    def get_connection(self):
        return self.conn

from django.test.testcases import TransactionTestCase
TransactionTestCase