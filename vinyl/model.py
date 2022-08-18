from django.db import router
# .connect(toppings_changed, sender=Pizza.toppings.through)

from django.db.models import DEFERRED, Model, ExpressionWrapper
from django.db.models.base import ModelBase
from django.db.models.functions import Coalesce

from vinyl import deferred
from vinyl.queryset import VinylQuerySet


class ModelMixin:

    def _get_pk_val(self, meta=None):
        meta = meta or self._meta
        return getattr(self, meta.pk.attname)

    def _set_pk_val(self, value):
        for parent_link in self._meta.parents.values():
            if parent_link and parent_link != self._meta.pk:
                setattr(self, parent_link.target_field.attname, value)
        return setattr(self, self._meta.pk.attname, value)

    pk = property(_get_pk_val, _set_pk_val)

    @classmethod
    def from_db(cls, db, field_names, values):
        if len(values) != len(cls._meta.concrete_fields):
            values_iter = iter(values)
            values = [
                next(values_iter) if f.attname in field_names else DEFERRED
                for f in cls._meta.concrete_fields
            ]
        new = cls(*values)
        new._state.adding = False
        new._state.db = db
        return new


class VinylMetaD:
    def __get__(self, instance, owner):
        return owner._model._meta


class SkipModelBase(ModelBase):
    """Metaclass for all models."""

    def __new__(cls, name, bases, attrs, **kwargs):
        return type.__new__(cls, name, bases, attrs)


class VinylModel(Model, metaclass=SkipModelBase):
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

    async def save(
            self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        async with deferred.driver():
            super().save(force_update=True, using=using, update_fields=update_fields)


    def _do_update(self, base_qs, using, pk_val, values, update_fields, forced_update):
        """
        Try to update the model. Return True if the model was updated (if an
        update query was done and a matching row was found in the DB).
        """
        filtered = base_qs.filter(pk=pk_val)
        if not values:
            return True
        filtered._update(values)
        return True

    async def _insert_table(self, cls, using=None):
        meta = cls._meta
        pk_val = self._get_pk_val(meta)
        if pk_val is None:
            pk_val = meta.pk.get_pk_value_on_save(self)
            setattr(self, meta.pk.attname, pk_val)
        pk_set = pk_val is not None
        fields = meta.local_concrete_fields
        if not pk_set:
            fields = [f for f in fields if f is not meta.auto_field]

        returning_fields = meta.db_returning_fields
        async with deferred.driver():
            results = self._do_insert(
                cls._base_manager, using, fields, returning_fields, raw=False
            )
        if results:
            for value, field in zip(results[0], returning_fields):
                setattr(self, field.attname, value)


    async def _insert_parents(self, cls, using):
        meta = cls._meta
        inserted = False
        for parent, field in meta.parents.items():
            # Make sure the link fields are synced between parent and self.
            if (
                field
                and getattr(self, parent._meta.pk.attname) is None
                and getattr(self, field.attname) is not None
            ):
                setattr(self, parent._meta.pk.attname, getattr(self, field.attname))
            await self._insert_parents(
                cls=parent, using=using
            )
            await self._insert_table(cls=parent, using=using)
            # Set the parent's PK value to self.
            if field:
                setattr(self, field.attname, self._get_pk_val(parent._meta))
                # Since we didn't have an instance of the parent handy set
                # attname directly, bypassing the descriptor. Invalidate
                # the related object cache, in case it's been accidentally
                # populated. A fresh instance will be re-built from the
                # database if necessary.
                if field.is_cached(self):
                    field.delete_cached_value(self)

    async def insert(self, using=None):
        self._prepare_related_fields_for_save(operation_name="save")
        using = using or router.db_for_write(self.__class__, instance=self)
        cls = origin = self.__class__
        # Skip proxies, but keep the origin as the proxy model.
        if cls._meta.proxy:
            cls = cls._meta.concrete_model
        meta = cls._meta

        # A transaction isn't needed if one query is issued.
        if meta.parents:
            await self._insert_parents(cls=cls, using=using)
        await self._insert_table(cls=cls, using=using)

    # async def insert(self):