"""
These patches are actually harmless

They are applied only in async context if the deferred execution is on
And when applied, they turn off transactions and signals
"""

from contextlib import contextmanager

from django.db import connection
from django.db.models.manager import ManagerDescriptor
from django.db.transaction import Atomic
from django.db.utils import ConnectionHandler


@contextmanager
def no_op():
    yield


class orig:
    class Atomic(Atomic):
        __enter__ = Atomic.__enter__
        __exit__ = Atomic.__exit__

#
# class SignalPatch:
#
#     def send(*args, **kwargs):
#         from vinyl.flags import is_vinyl
#         #TODO only for async
#         if is_vinyl.get():
#             return
#         return Signal.send(*args, **kwargs)
#
#     def send_robust(*args, **kwargs):
#         from vinyl.flags import is_vinyl
#         if is_vinyl.get():
#             return
#         return Signal.send_robust(*args, **kwargs)
#

@contextmanager
def apply():
    Atomic__enter__ = Atomic.__enter__
    Atomic__exit__ = Atomic.__exit__
    # Signal_send = Signal.send
    # Signal_send_robust = Signal.send_robust
    try:
        Atomic.__enter__ = Atomic.__exit__ = lambda *args, **kw: None
        # Signal.send = SignalPatch.send
        # Signal.send_robust = SignalPatch.send_robust
        yield
    finally:
        Atomic.__enter__ = Atomic__enter__
        Atomic.__exit__ = Atomic__exit__
        # Signal.send = Signal_send
        # Signal.send_robust = Signal_send_robust


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
            print('models_ready')
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

# from django.test.testcases import TestCase
#
# class TestCasePatch:
#
#     def _post_teardown(self, *, _post_teardown=TestCase._post_teardown):
#         restore_DATABASES()
#         return _post_teardown(self)
#
#     def _pre_setup(self, *, _pre_setup=TestCase._pre_setup):
#         ret = _pre_setup(self)
#         replace_DATABASES()
#
#         for app_name, app in apps.app_configs.items():
#             for model_name, model in app.models.items():
#                 mgr = model.objects
#                 from vinyl.queryset import VinylQuerySet
#                 if issubclass(mgr._queryset_class, VinylQuerySet):
#                     continue
#                 from vinyl.meta import make_vinyl_model
#                 mgr.model = make_vinyl_model(mgr.model)
#                 mgr_class = mgr.from_queryset(VinylQuerySet)
#                 mgr.__class__ = mgr_class
#
#         return ret


def patch_manager():
    #TODO just change .manager in descriptor
    for app_name, app in apps.app_configs.items():
        for model_name, model in app.models.items():
            mgr = model.objects
            from vinyl.queryset import VinylQuerySet
            if issubclass(mgr._queryset_class, VinylQuerySet):
                continue
            from vinyl.meta import make_vinyl_model
            mgr.model = make_vinyl_model(mgr.model)
            mgr._db = f'vinyl_{mgr._db}'
            mgr_class = mgr.from_queryset(VinylQuerySet)
            mgr.__class__ = mgr_class


from django.test.testcases import TransactionTestCase


class TransactionalTestCasePatch:

    # @in_transaction()
    def run(self, result=None, run=TransactionTestCase.run):
        patch_manager()
        run(self, result)
        connection.close()

TransactionTestCase.run = TransactionalTestCasePatch.run


# class C:1
#
# @patch.apply
# class C(C, metaclass=patch):
#
#     def f(self, f=C.f):
#         f()