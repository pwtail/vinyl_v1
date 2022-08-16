from vinyl import deferred


class ManyToManyDescriptor:

    def __get__(self, instance, owner):
        django_model = owner._model
        wrapped = getattr(django_model, self.name)
        manager = wrapped.__get__(instance, owner)
        # manager.__class__ = wrap_related_manager(manager.__class__)
        if wrapper := getattr(manager, 'vinyl_wrapper', None):
            return wrapper
        manager.vinyl_wrapper = Wrapper(manager)
        return manager.vinyl_wrapper


    def __set_name__(self, owner, name):
        self.name = name


class Wrapper:
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