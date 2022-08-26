from contextlib import contextmanager

from django.db.transaction import Atomic
from django.dispatch import Signal

from vinyl.deferred import statements


@contextmanager
def no_op():
    yield


class AtomicPatch:

    def __new__(cls, *args, **kwargs):
        if statements.get(None) is not None:
            return no_op()
        return super().__new__(cls)


class SignalPatch:

    def send(*args, **kwargs):
        if statements.get(None) is not None:
            return
        return Signal.send(*args, **kwargs)

    def send_robust(*args, **kwargs):
        if statements.get(None) is not None:
            return
        return Signal.send_robust(*args, **kwargs)


@contextmanager
def apply():
    Atomic__new__ = Atomic.__new__
    Signal_send = Signal.send
    Signal_send_robust = Signal.send_robust
    try:
        Atomic.__new__ = AtomicPatch.__new__
        Signal.send = SignalPatch.send
        Signal.send_robust = SignalPatch.send_robust
        yield
    finally:
        Atomic.__new__ = Atomic__new__
        Signal.send = Signal_send
        Signal.send_robust = Signal_send_robust