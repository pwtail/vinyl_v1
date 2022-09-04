from contextlib import contextmanager, contextmanager
from contextvars import ContextVar


class BackendInterface:

    # common

    @contextmanager
    def cursor(self):
        yield

    @contextmanager
    def transaction(self):
        yield

    def execute_sql(self, sql, params):
        pass

    def execute_only(self, sql, params):
        pass

    @contextmanager
    def set_connection(self, conn):
        yield

    def get_connection(self):
        pass

    # async-only

    async_pool = None
    async_connection = ContextVar('async_connection', default=None)

    def start_pool(self):
        pass

    @contextmanager
    def get_connection_from_pool(self):
        yield



