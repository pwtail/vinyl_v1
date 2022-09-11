"""
These patches are actually harmless

They are applied only in async context if the deferred execution is on
And when applied, they turn off transactions and signals
"""

from contextlib import contextmanager

from django.db.models.manager import ManagerDescriptor
from django.db.transaction import Atomic
from django.db.utils import ConnectionHandler
from django.dispatch import Signal


@contextmanager
def no_op():
    yield


class orig:
    class Atomic(Atomic):
        __new__ = Atomic.__new__


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
    Atomic__enter__ = Atomic.__enter__
    Atomic__exit__ = Atomic.__exit__
    Signal_send = Signal.send
    Signal_send_robust = Signal.send_robust
    try:
        Atomic.__enter__ = Atomic.__exit__ = lambda *args, **kw: None
        Signal.send = SignalPatch.send
        Signal.send_robust = SignalPatch.send_robust
        yield
    finally:
        Atomic.__enter__ = Atomic__enter__
        Atomic.__exit__ = Atomic__exit__
        Signal.send = Signal_send
        Signal.send_robust = Signal_send_robust


class ModelsReady:

    def __get__(self, instance, owner):
        assert instance
        return instance.__dict__['models_ready']

    def __set__(self, instance, value):
        assert instance
        old_val = instance.__dict__.get('models_ready')
        if old_val is False and value is True:
            from vinyl.signals import models_ready as _signal
            _signal.send(ModelsReady)
        instance.__dict__['models_ready'] = value

    def __set_name__(self, owner, name):
        assert name == 'models_ready'


from django.apps import apps
from django.apps.registry import Apps

class Apps(Apps):
    models_ready = ModelsReady()


class DescriptorPatch:
    # used for testing

    @classmethod
    def apply(cls):
        ManagerDescriptor.__get__ = cls.__get__

    def __get__(self, instance, cls, __get__=ManagerDescriptor.__get__):
        mgr = __get__(self, instance, cls)
        from vinyl.queryset import VinylQuerySet
        if issubclass(mgr._queryset_class, VinylQuerySet):
            return mgr
        from vinyl.meta import make_vinyl_model
        mgr.model = make_vinyl_model(mgr.model)
        mgr_class = mgr.from_queryset(VinylQuerySet)
        mgr.__class__ = mgr_class
        return mgr


class ConnectionHandlerPatch:

    @classmethod
    def apply(cls):
        ConnectionHandler.__getitem__ = cls.__getitem__

    def __getitem__(ch, alias,
                    __getitem__=ConnectionHandler.__getitem__):
        conn = __getitem__(ch, alias)
        from vinyl.flags import is_vinyl
        if is_vinyl.get():
            return conn
        return conn._fallback


# APPLY:

apps.__class__ = Apps
ConnectionHandlerPatch.apply()