import threading
from contextlib import contextmanager

tlocal = threading.local()


@contextmanager
def tlocal_context(key):
    val = {}
    setattr(tlocal, key, val)
    try:
        yield val
    finally:
        delattr(tlocal, key)