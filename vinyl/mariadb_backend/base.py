from contextlib import asynccontextmanager

import aiomysql
from django.db.backends.mysql.base import DatabaseWrapper as _DatabaseWrapper

from vinyl.backend_impl import VinylConnectionMixin
from vinyl.mariadb_backend.ops import DatabaseOperations


class DatabaseWrapper(VinylConnectionMixin, _DatabaseWrapper):
    ops_class = DatabaseOperations

    def get_connection_params(self):
        kwargs = {}
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
        await self.get_mysql_server_data()
        return self.async_pool

    @asynccontextmanager
    async def get_connection_from_pool(self):
        if self.async_pool is None:
            await self.start_pool()
        async with self.async_pool.acquire() as conn:
            try:
                yield conn
            except:
                await conn.rollback()
                raise
            else:
                await conn.commit()

    async def get_mysql_server_data(self):
        async with self.cursor() as cursor:
            # Select some server variables and test if the time zone
            # definitions are installed. CONVERT_TZ returns NULL if 'UTC'
            # timezone isn't loaded into the mysql.time_zone table.
            await cursor.execute(
                """
                SELECT VERSION(),
                       @@sql_mode,
                       @@default_storage_engine,
                       @@sql_auto_is_null,
                       @@lower_case_table_names,
                       CONVERT_TZ('2001-01-01 01:00:00', 'UTC', 'UTC') IS NOT NULL
            """
            )
            row = await cursor.fetchone()
        self.mysql_server_data = {
            "version": row[0],
            "sql_mode": row[1],
            "default_storage_engine": row[2],
            "sql_auto_is_null": bool(row[3]),
            "lower_case_table_names": bool(row[4]),
            "has_zoneinfo_database": bool(row[5]),
        }
        return self.mysql_server_data