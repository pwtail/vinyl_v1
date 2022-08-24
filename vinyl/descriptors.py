from django.db import router
from django.db.models import ForeignKey
from django.db.models.fields.related_descriptors import ForeignKeyDeferredAttribute

from vinyl import deferred
from vinyl.queryset import VinylQuerySet


class FKDescriptor:
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __set_name__(self, owner, name):
        self.name = name

    def __set__(self, instance, value):
        return self.wrapped.__set__(instance, value)

    def __get__(self, instance, owner):
        django_model = owner._model
        attr = getattr(django_model, self.name)
        if instance is None:
            return attr.__get__(None, django_model)
        qs = attr.get_queryset(instance=instance)
        from vinyl.queryset import VinylQuerySet
        qs = VinylQuerySet.clone(qs)
        # Assuming the database enforces foreign keys, this won't fail.
        return qs.filter(attr.field.get_reverse_related_filter(instance)).get_or_none()


class RelatedManagerDescriptor:
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __set__(self, instance, value):
        return self.wrapped.__set__(instance, value)

    def __get__(self, instance, owner):
        django_model = owner._model
        attr = getattr(django_model, self.name)
        if instance is None:
            return attr.__get__(None, django_model)
        manager = attr.__get__(instance, owner)
        # manager.__class__ = wrap_related_manager(manager.__class__)
        if wrapper := getattr(manager, 'vinyl_wrapper', None):
            #???
            return wrapper
        if (field := getattr(manager, 'field', None)) and isinstance(field, ForeignKey):
            manager_cls = ReverseManyToOneManager
        else:
            manager_cls = M2MManager
        manager.vinyl_wrapper = manager_cls(manager)
        return manager.vinyl_wrapper

    def __set_name__(self, owner, name):
        self.name = name


class RelatedManagerWrapper:
    def __init__(self, manager):
        self.rel_mgr = manager

    #TODO ???
    def __getattr__(self, item):
        return getattr(self.rel_mgr, item)

    async def add(self, *args, **kw):
        async with deferred.driver():
            self.rel_mgr.add(*args, **kw)

    async def remove(self, *args, **kw):
        async with deferred.driver():
            self.rel_mgr.remove(*args, **kw)

    async def clear(self, *args, **kw):
        async with deferred.driver():
            self.rel_mgr.clear(*args, **kw)

    def all(self):
        qs = self.rel_mgr.all()
        return VinylQuerySet.clone(qs)


    def __await__(self):
        return self.all().__await__()

class M2MManager(RelatedManagerWrapper):

    async def set(self, objs, *, through_defaults=None):
        objs = tuple(objs)

        db = router.db_for_write(self.through, instance=self.instance)
        qs = self.using(db).values_list(
            self.target_field.target_field.attname, flat=True
        )
        qs = VinylQuerySet.clone(qs)
        old_ids = set(await qs)

        new_objs = []
        for obj in objs:
            fk_val = (
                self.target_field.get_foreign_related_value(obj)[0]
                if isinstance(obj, self.model)
                else self.target_field.get_prep_value(obj)
            )
            if fk_val in old_ids:
                old_ids.remove(fk_val)
            else:
                new_objs.append(obj)

        await self.remove(*old_ids)
        await self.add(*new_objs, through_defaults=through_defaults)


class ReverseManyToOneManager(RelatedManagerWrapper):

    async def set(self, objs, *, bulk=True, clear=False):
        self._check_fk_val()
        # Force evaluation of `objs` in case it's a queryset whose value
        # could be affected by `manager.clear()`. Refs #19816.
        objs = tuple(objs)

        if self.field.null:
            db = router.db_for_write(self.model, instance=self.instance)
            old_objs = self.using(db).all()
            old_objs = await VinylQuerySet.clone(old_objs)
            new_objs = []
            for obj in objs:
                if obj in old_objs:
                    old_objs.remove(obj)
                else:
                    new_objs.append(obj)

            await self.remove(*old_objs, bulk=bulk)
            await self.add(*new_objs, bulk=bulk)
        else:
            await self.add(*objs, bulk=bulk)