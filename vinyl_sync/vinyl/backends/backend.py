from contextlib import contextmanager, contextmanager
from functools import cached_property


@contextmanager
def no_op():
    yield


class Backend:
    connection = None

    def execute_sql(self, sql, params):
        """
        Execute and fetch multiple rows
        """
        with self.cursor() as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()
            return (results,)

    def execute_only(self, sql, params):
        """
        Execute but do not fetch
        """
        with self.cursor() as cursor:
            cursor.execute(sql, params)

    def transaction(self):
        raise NotImplementedError

    def CursorWrapper(self, cursor):
        return cursor

    @cached_property
    def ops(self):
        return self.ops_class(self)

    def __init__(self, *args, **kw):
        self._fallback = self.fallback_class(*args, **kw)

    def __getattr__(self, name):
        return getattr(self._fallback, name)


class PooledBackend(Backend):
    pool = None

    @contextmanager
    def cursor(self):
        if (conn := self.get_connection()) is not None:
            with conn.cursor() as cur:
                yield self.CursorWrapper(cur)
            return
        with self.get_connection_from_pool() as conn:
            with conn.cursor() as cur:
                yield self.CursorWrapper(cur)

    def transaction(self):
        if self.get_connection() is not None:
            return no_op()
        return self.get_connection_from_pool()

    @contextmanager
    def get_connection_from_pool(self):
        if self.pool is None:
            self.start_pool()
        raise NotImplementedError

    def start_pool(self):
        raise NotImplementedError
