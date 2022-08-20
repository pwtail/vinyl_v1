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
        manager.vinyl_wrapper = RelatedManagerWrapper(manager)
        return manager.vinyl_wrapper

    def __set_name__(self, owner, name):
        self.name = name


class RelatedManagerWrapper:
    def __init__(self, manager):
        self.rel_mgr = manager

    async def add(self, *args, **kw):
        async with deferred.driver():
            self.rel_mgr.add(*args, **kw)

    async def set(self, *args, **kw):
        async with deferred.driver():
            self.rel_mgr.set(*args, **kw)

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