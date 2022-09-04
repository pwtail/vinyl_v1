from contextlib import contextmanager

from django.db import router
from django.db.models import Model
from django.db.models.base import ModelBase

from vinyl.deferred import deferred
from vinyl.insert import InsertMixin
from vinyl.util import set_class


class VinylMetaD:
    def __get__(self, instance, owner):
        return owner._deferred_model._meta


class SkipModelBase(ModelBase):
    def __new__(cls, name, bases, attrs, **kwargs):
        return type.__new__(cls, name, bases, attrs)


class DeferredModel(Model, metaclass=SkipModelBase):
    """
    The same as Model, just able to work for deferred execution too.
    """

    def _do_update(self, base_qs, using, pk_val, values, update_fields, forced_update):
        """
        Always return True
        """
        filtered = base_qs.filter(pk=pk_val)
        if not values:
            return True
        filtered._update(values)
        return True


class VinylModel(InsertMixin, DeferredModel, metaclass=SkipModelBase):
    _deferred_model = None
    _meta = VinylMetaD()

    #TODO is it used?
    def __new__(cls, *args, **kwargs):
        ob = cls._deferred_model(*args, **kwargs)
        ob._prefetch_cache = {}
        ob.__class__ = cls
        return ob

    def __getitem__(self, item):
        if (value := self._prefetched_objects_cache.get(item)) is not None:
            return value
        return self._state.fields_cache[item]

    @contextmanager
    def _deferred(self):
        with deferred():
            with set_class(self, self._deferred_model):
                yield

    def save(self, update_fields=None):
        """
        Always do an update
        """
        with self._deferred():
            Model.save(self, force_update=True, update_fields=update_fields)

    def delete(self, using=None, keep_parents=False):
        with self._deferred():
            Model.delete(self, using=using, keep_parents=keep_parents)
