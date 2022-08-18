from django.db import router
from django.db.models import Model
from django.db.models.base import ModelBase

from vinyl import deferred
from vinyl.saving import SaveMixin


# .connect(toppings_changed, sender=Pizza.toppings.through)

#
# class ModelMixin:
#
#     def _get_pk_val(self, meta=None):
#         meta = meta or self._meta
#         return getattr(self, meta.pk.attname)
#
#     def _set_pk_val(self, value):
#         for parent_link in self._meta.parents.values():
#             if parent_link and parent_link != self._meta.pk:
#                 setattr(self, parent_link.target_field.attname, value)
#         return setattr(self, self._meta.pk.attname, value)
#
#     pk = property(_get_pk_val, _set_pk_val)
#
#     @classmethod
#     def from_db(cls, db, field_names, values):
#         if len(values) != len(cls._meta.concrete_fields):
#             values_iter = iter(values)
#             values = [
#                 next(values_iter) if f.attname in field_names else DEFERRED
#                 for f in cls._meta.concrete_fields
#             ]
#         new = cls(*values)
#         new._state.adding = False
#         new._state.db = db
#         return new
#

class VinylMetaD:
    def __get__(self, instance, owner):
        return owner._model._meta


class SkipModelBase(ModelBase):
    def __new__(cls, name, bases, attrs, **kwargs):
        return type.__new__(cls, name, bases, attrs)


class VinylModel(SaveMixin, Model, metaclass=SkipModelBase):
    _model = None
    _meta = VinylMetaD()

    #TODO __init__?
    def __new__(cls, *args, **kwargs):
        ob = cls._model(*args, **kwargs)
        ob._prefetch_cache = {}
        ob.__class__ = cls
        return ob

    def __getitem__(self, item):
        if value := self._prefetched_objects_cache.get(item) is not None:
            return value
        return self._state.fields_cache[item]
