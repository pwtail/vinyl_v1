from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar


class BackendInterface:

    # common

    @asynccontextmanager
    async def cursor(self):
        yield

    @asynccontextmanager
    async def transaction(self):
        yield

    async def execute_sql(self, sql, params):
        pass

    async def execute_only(self, sql, params):
        pass

    @contextmanager
    def set_connection(self, conn):
        yield

    def get_connection(self):
        pass

    # async-only

    async_pool = None
    async_connection = ContextVar('async_connection', default=None)

    async def start_pool(self):
        pass

    @asynccontextmanager
    async def get_connection_from_pool(self):
        yield



