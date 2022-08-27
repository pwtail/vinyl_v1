from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar


@contextmanager
def no_op():
    yield


class VinylConnectionMixin:
    async_pool = None
    async_connection = ContextVar('async_connection', default=None)

    CursorWrapper = None

    @asynccontextmanager
    async def cursor(self):
        if (conn := self.async_connection.get()) is not None:
            async with conn.cursor() as cur:
                if self.CursorWrapper:
                    cur = self.CursorWrapper(cur)
                yield cur
            return
        async with self.get_connection_from_pool() as conn:
            token = self.async_connection.set(conn)
            try:
                async with conn.cursor() as cur:
                    if self.CursorWrapper:
                        cur = self.CursorWrapper(cur)
                    yield cur
            finally:
                self.async_connection.reset(token)

    def transaction(self):
        if self.async_connection.get():
            return no_op()
        return self.get_connection_from_pool()

    async def start_pool(self):
        raise NotImplementedError

    @asynccontextmanager
    async def get_connection_from_pool(self):
        raise NotImplementedError()

    async def execute_sql(self, sql, params):
        """
        Execute and fetch multiple rows
        """
        async with self.cursor() as cursor:
            await cursor.execute(sql, params)
            results = await cursor.fetchall()
            return (results,)  # FIXME

    async def execute_only(self, sql, params):
        """
        Execute but do not fetch
        """
        async with self.cursor() as cursor:
            await cursor.execute(sql, params)
