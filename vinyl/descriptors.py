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
        print('name', name)


class Wrapper:
    def __init__(self, manager):
        self.manager = manager

    async def add(self, *objs):
        async with deferred.driver():
            self.manager.add(*objs)