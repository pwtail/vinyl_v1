import threading
import typing
from collections import deque
from contextlib import asynccontextmanager
from contextvars import ContextVar

from django.db import connections

from vinyl import patches

# TODO rename?
statements = ContextVar('statements')


class StatementsList(list):
    using = None


@asynccontextmanager
async def driver():
    token = statements.set(value := StatementsList())
    try:
        with patches.apply():
            yield value
        if not value:
            return
        connection = connections[value.using]
        async with connection.transaction():
            for sql, params in value:
                await connection.execute_only(sql, params)
    finally:
        statements.reset(token)

#TODO deferred mixin
