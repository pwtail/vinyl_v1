from contextlib import contextmanager

from django.db.transaction import Atomic

from vinyl.deferred import statements


@contextmanager
def no_op():
    yield

class AtomicPatch:

    def __new__(cls, *args, **kwargs):
        if statements.get(None) is not None:
            return no_op()
        return super(Atomic, cls).__new__(cls)


Atomic.__new__ = AtomicPatch.__new__
