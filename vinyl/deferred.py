import threading
import typing
from collections import deque
from contextlib import asynccontextmanager
from contextvars import ContextVar

from vinyl import patches

# TODO rename?
statements = ContextVar('statements')



class Statement(typing.NamedTuple):
    sql: str
    params: tuple
    using: str


#TODO using
@asynccontextmanager
async def driver():
    token = statements.set(value := deque())
    try:
        with patches.apply():
            yield value
        await execute_statements(value)
    finally:
        if value:
            print('not all statements did execute')
        statements.reset(token)


@atomic()
async def execute_statements(statements):
    # TODO use pool
    import psycopg
    async with await psycopg.AsyncConnection.connect(
            "dbname=lulka user=postgres"
    ) as aconn:
        while statements:
            sql, params = statements.popleft()
            async with aconn.cursor() as cursor:
                print(sql, params)
                await cursor.execute(sql, params)