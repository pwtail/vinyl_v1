from contextlib import asynccontextmanager, contextmanager
from functools import cached_property


@contextmanager
def no_op():
    yield


class Backend:
    connection = None

    async def execute_sql(self, sql, params):
        """
        Execute and fetch multiple rows
        """
        async with self.cursor() as cursor:
            await cursor.execute(sql, params)
            results = await cursor.fetchall()
            return (results,)

    async def execute_only(self, sql, params):
        """
        Execute but do not fetch
        """
        async with self.cursor() as cursor:
            await cursor.execute(sql, params)

    def transaction(self):
        raise NotImplementedError

    def CursorWrapper(self, cursor):
        return cursor

    @cached_property
    def ops(self):
        return self.ops_class(self)

    def __init__(self, *args, **kw):
        self._fallback = self.fallback_class(*args, **kw)

    def __getattr__(self, name):
        return getattr(self._fallback, name)


class PooledBackend(Backend):
    pool = None

    @asynccontextmanager
    async def cursor(self):
        if (conn := self.get_connection()) is not None:
            async with conn.cursor() as cur:
                yield self.CursorWrapper(cur)
            return
        async with self.get_connection_from_pool() as conn:
            async with conn.cursor() as cur:
                yield self.CursorWrapper(cur)

    def transaction(self):
        if self.get_connection() is not None:
            return no_op()
        return self.get_connection_from_pool()

    @asynccontextmanager
    async def get_connection_from_pool(self):
        if self.pool is None:
            await self.start_pool()
        raise NotImplementedError

    async def start_pool(self):
        raise NotImplementedError