import threading
from collections import deque
from contextlib import asynccontextmanager
from contextvars import ContextVar

# TODO rename?
statements = ContextVar('statements')

def add_statement(*stmt):
    statements.get().append(stmt)


@asynccontextmanager
async def driver():
    token = statements.set(value := deque())
    try:
        yield value
        await execute_statements(value)
    finally:
        if value:
            print('not all statements did execute')
        statements.reset(token)


# transaction?
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