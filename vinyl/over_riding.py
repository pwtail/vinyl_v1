import inspect
from functools import cached_property

from django.db.models import Model


# ride = over(C)
# @Override



class over:
    registry = {}

    def __init__(self, parent):
        self.parent = parent
        self.inserts = []

    @cached_property
    def file(self):
        return inspect.getfile(self.parent)

    def ride(self, fn):
        1

    def __call__(self, fn):
        target = getattr(self.parent, fn.__name__)
        line = target.__code__.co_firstlineno - 1
        self.inserts.append(line)
        self.registry[target] = fn

        # def wrapper(fn)

        return fn


def Override(fn):
    return over.registry[fn]

ride = over(Model)


class Model(Model):

    @ride
    def save(self, *args, **kw):
        print('Do nothing.')

