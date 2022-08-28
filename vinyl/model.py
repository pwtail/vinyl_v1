from contextlib import asynccontextmanager

from django.db import router
from django.db.models import Model
from django.db.models.base import ModelBase
from django.db.models.query_utils import DeferredAttribute

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

    #TODO is it used?
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
    async def _deferred(self):
        async with deferred.driver():
            cls = self.__class__
            self.__class__ = self._model
            try:
                yield
            finally:
                self.__class__ = cls

    def get_vinyl_db(self, using):
        using = using or router.db_for_write(self.__class__, instance=self)
        if not using.startswith('vinyl_'):
            return f'vinyl_{using}'

    async def save(self, using=None, update_fields=None):
        """
        Always do an update
        """
        using = self.get_vinyl_db(using)
        async with self._deferred():
            Model.save(self, force_update=True, using=using, update_fields=update_fields)

    async def delete(self, using=None, keep_parents=False):
        using = self.get_vinyl_db(using)
        async with self._deferred():
            Model.delete(self, using=using, keep_parents=keep_parents)

    @classmethod
    def inherit(cls, model):
        if hasattr(model, 'vinyl_model'):
            return model.vinyl_model
        ns = cls._copy_namespace(model)
        newcls = model.vinyl_model = type(model.__name__, (VinylModel, model), ns)
        newcls._model = type(model.__name__, (ModelPlus, model), {})
        return newcls

    @staticmethod
    def _copy_namespace(model):
        ns = {}
        model_vars = {
            field.name: getattr(model, field.name)
            for field in model._meta.fields
        }
        model_vars.update(vars(model))
        parent_fields = set(model._meta.parents.values())
        for key, val in model_vars.items():
            if (
            field := getattr(val, 'field', None)) and val.__module__ == 'django.db.models.fields.related_descriptors':
                if field in parent_fields:
                    continue
                if isinstance(val, DeferredAttribute):
                    continue
                if hasattr(val, 'rel_mgr') or hasattr(val, 'related_manager_cls'):
                    from vinyl.descriptors import RelatedManagerDescriptor
                    val = RelatedManagerDescriptor(val)
                else:
                    from vinyl.descriptors import FKDescriptor
                    val = FKDescriptor(val)
                ns[key] = val
        return ns