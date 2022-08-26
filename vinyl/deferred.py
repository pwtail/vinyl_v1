import threading
import typing
from collections import deque
from contextlib import asynccontextmanager
from contextvars import ContextVar

from django.db import connections

from vinyl import patches

# TODO rename?
statements = ContextVar('statements')



class Statement(typing.NamedTuple):
    sql: str
    params: tuple
    using: str


class StatementsDeque(deque):
    using = None

    def __bool__(self):
        return super().__bool__()


@asynccontextmanager
async def driver():
    token = statements.set(value := StatementsDeque())
    try:
        with patches.apply():
            yield value
        connection = connections[value.using]
        async with connection.transaction():
            for sql, params in value:
                await connection.execute_only(sql, params)
    finally:
        if value:
            print('not all statements did execute')
        statements.reset(token)

