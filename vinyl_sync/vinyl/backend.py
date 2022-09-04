from contextlib import contextmanager, contextmanager

from vinyl.flags import is_async


@contextmanager
def no_op():
    yield


class Backend:

    connection = None
    pool = None

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
        if self.connection:
            return no_op()
        return self.get_connection_from_pool()

    @contextmanager
    def get_connection_from_pool(self):
        if self.pool is None:
            self.start_pool()
        raise NotImplementedError

    def start_pool(self):
        raise NotImplementedError

    def CursorWrapper(self, cursor):
        return cursor