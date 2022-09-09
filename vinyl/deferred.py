import threading
from contextlib import asynccontextmanager, contextmanager

from django.db import connections

from vinyl import patches
from vinyl.flags import use_vinyl


class StatementsList(list):
    using = None


async def execute_statements(items):
    if not items:
        return
    connection = connections[items.using]
    async with connection.transaction():
        for sql, params in items:
            await connection.execute_only(sql, params)


tl = threading.local()
tl.collected_sql = None

@contextmanager
def collect_sql():
    tl.collected_sql = value = StatementsList()
    try:
        with patches.apply():
            yield value
    finally:
        tl.collected_sql = None

# is collecting sql
# get collected sql

def is_collecting_sql():
    return tl.collected_sql is not None


@asynccontextmanager
async def deferred():
    async with use_vinyl():
        with collect_sql() as items:
            yield
        await execute_statements(items)