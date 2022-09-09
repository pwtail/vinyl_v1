import threading
from contextlib import contextmanager, contextmanager

from django.db import connections

from vinyl import patches
from vinyl.flags import use_vinyl


class StatementsList(list):
    using = None


def execute_statements(items):
    if not items:
        return
    connection = connections[items.using]
    with connection.transaction():
        for sql, params in items:
            connection.execute_only(sql, params)


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


@contextmanager
def deferred():
    with use_vinyl():
        with collect_sql() as items:
            yield
        execute_statements(items)