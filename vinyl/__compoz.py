#TODO DELETE
import typing


from django.db.models import Model as DjangoModel
from django.db.models.query_utils import DeferredAttribute


class NotTuple(Exception):
    pass





class Model(typing.NamedTuple):
    #TODO wrapped?
    obj: DjangoModel

    @classmethod
    def make_new(cls, **kwargs):
        1

    def __iter__(self):
        raise NotTuple

    def __getitem__(self, item):
        if isinstance(item, int):
            raise NotTuple

    async def save(self):
        1


class DeferredAttributeWrapper:
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __get__(self, instance, owner):
        if instance:
            instance = instance.obj
        owner = owner._model
        return self.wrapped.__get__(instance, owner)


def make(model):
    # copy
    ns = {'_model': model}
    for k, v in model.__dict__.items():
        if isinstance(v, DeferredAttribute):
            new_v = DeferredAttributeWrapper(v)
            ns[k] = new_v

    cls = type(model.__name__, (Model,), ns)
    return cls