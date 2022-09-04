"""
These patches are actually harmless

They are applied only in context if the deferred execution is on
And when applied, they turn off transactions and signals
"""

from contextlib import contextmanager

from django.db.transaction import Atomic
from django.dispatch import Signal


@contextmanager
def no_op():
    yield


class AtomicPatch:

    def __new__(cls, *args, **kwargs):
        from vinyl.deferred import is_collecting_sql
        if is_collecting_sql():
            return no_op()
        return super().__new__(cls)


class SignalPatch:

    def send(*args, **kwargs):
        from vinyl.deferred import is_collecting_sql
        if is_collecting_sql():
            return
        return Signal.send(*args, **kwargs)

    def send_robust(*args, **kwargs):
        from vinyl.deferred import is_collecting_sql
        if is_collecting_sql():
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


class ModelReadyDescriptor:

    def __get__(self, instance, owner):
        assert instance
        return instance.__dict__['models_ready']

    def __set__(self, instance, value):
        assert instance
        old_val = instance.__dict__.get('models_ready')
        if old_val is False and value is True:
            from vinyl.manager import init_models
            init_models.send(Signal)
        instance.__dict__['models_ready'] = value

    def __set_name__(self, owner, name):
        assert name == 'models_ready'


from django.apps import apps
from django.apps.registry import Apps

class Apps(Apps):
    models_ready = ModelReadyDescriptor()

apps.__class__ = Apps