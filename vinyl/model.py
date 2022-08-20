from contextlib import asynccontextmanager

from django.db import router
from django.db.models import Model
from django.db.models.base import ModelBase

from vinyl import deferred
from vinyl.saving import SaveMixin


class VinylMetaD:
    def __get__(self, instance, owner):
        return owner._model._meta


class SkipModelBase(ModelBase):
    def __new__(cls, name, bases, attrs, **kwargs):
        return type.__new__(cls, name, bases, attrs)


class ModelPlus(Model, metaclass=SkipModelBase):

    def _do_update(self, base_qs, using, pk_val, values, update_fields, forced_update):
        """
        Always return True
        """
        filtered = base_qs.filter(pk=pk_val)
        if not values:
            return True
        filtered._update(values)
        return True


class VinylModel(SaveMixin, ModelPlus, metaclass=SkipModelBase):
    _model = None
    _meta = VinylMetaD()

    #TODO __init__?
    def __new__(cls, *args, **kwargs):
        ob = cls._model(*args, **kwargs)
        ob._prefetch_cache = {}
        ob.__class__ = cls
        return ob

    def __getitem__(self, item):
        if (value := self._prefetched_objects_cache.get(item)) is not None:
            return value
        return self._state.fields_cache[item]

    @asynccontextmanager
    async def ctx(self):
        async with deferred.driver():
            cls = self.__class__
            self.__class__ = self._model
            try:
                yield
            finally:
                self.__class__ = cls

    async def save(self, using=None, update_fields=None):
        """
        Always do an update
        """
        async with self.ctx():
            Model.save(self, force_update=True, using=using, update_fields=update_fields)

    async def delete(self, using=None, keep_parents=False):
        async with self.ctx():
            super().delete(using=using, keep_parents=keep_parents)
