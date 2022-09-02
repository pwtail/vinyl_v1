from contextlib import contextmanager

from django.db.models import QuerySet


def Await(obj):
    if isinstance(obj, QuerySet):
        from vinyl.queryset import VinylQuerySet
        return VinylQuerySet.__Await__(obj)
    return obj.__Await__()


@contextmanager
def set_class(obj, new_cls):
    cls = obj.__class__
    obj.__class__ = new_cls
    try:
        yield
    finally:
        obj.__class__ = cls