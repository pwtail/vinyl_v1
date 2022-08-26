from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar

from django.db.backends.mysql.base import DatabaseWrapper as _DatabaseWrapper, django_conversions

from vinyl.mariadb_backend.ops import DatabaseOperations

import aiomysql

@contextmanager
def no_op():
    yield


class DatabaseWrapper(_DatabaseWrapper):
    ops_class = DatabaseOperations

    async_pool = None
    async_connection = ContextVar('async_connection', default=None)

    CursorWrapper = None

    async def execute_sql(self, sql, params):
        """
        Execute and fetch multiple rows
        """
        async with self.cursor() as cursor:
            await cursor.execute(sql, params)
            results = await cursor.fetchall()
            return (results,)  # FIXME

    def get_connection_params(self):
        kwargs = {
            # "conv": django_conversions,
            # "charset": "utf8",
        }
        settings_dict = self.settings_dict
        if settings_dict["USER"]:
            kwargs["user"] = settings_dict["USER"]
        if settings_dict["NAME"]:
            kwargs["db"] = settings_dict["NAME"]
        if settings_dict["PASSWORD"]:
            kwargs["password"] = settings_dict["PASSWORD"]
        if settings_dict["HOST"].startswith("/"):
            kwargs["unix_socket"] = settings_dict["HOST"]
        elif settings_dict["HOST"]:
            kwargs["host"] = settings_dict["HOST"]
        if settings_dict["PORT"]:
            kwargs["port"] = int(settings_dict["PORT"])
        return kwargs

    async def start_pool(self):
        kwargs = self.get_connection_params()
        self.async_pool = await aiomysql.create_pool(**kwargs)
        return self.async_pool


    #split into conn & cursor
    @asynccontextmanager
    async def cursor(self):
        if self.async_pool is None:
            await self.start_pool()
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

    @asynccontextmanager
    async def get_connection_from_pool(self):
        if self.async_pool is None:
            await self.start_pool()
        async with self.async_pool.acquire() as conn:
            try:
                yield conn
            except:
                await conn.rollback()
            else:
                await conn.commit()

    async def execute_only(self, sql, params):
        """
        Execute but do not fetch
        """
        async with self.cursor() as cursor:
            await cursor.execute(sql, params)