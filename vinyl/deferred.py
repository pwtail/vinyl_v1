import threading
from collections import deque
from contextlib import asynccontextmanager

tlocal = threading.local()
tlocal.statements = None

def add_statement(*stmt):
    tlocal.statements.append(stmt)
#
# async with driver():
#   set contextvar

@asynccontextmanager
async def driver():
    assert not tlocal.statements
    tlocal.statements = deque()
    try:
        yield tlocal.statements
        await execute_statements()
    finally:
        if tlocal.statements:
            print('not all statements did execute')


# transaction?
async def execute_statements():
    # TODO use pool
    import psycopg
    async with await psycopg.AsyncConnection.connect(
            "dbname=lulka user=postgres"
    ) as aconn:
        while tlocal.statements:
            sql, params = tlocal.statements.popleft()
            async with aconn.cursor() as cursor:
                print(sql, params)
                await cursor.execute(sql, params)