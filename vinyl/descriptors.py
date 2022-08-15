from vinyl import deferred


#lazy ??????

class ManyToManyDescriptor:

    def __get__(self, instance, owner):
        django_model = owner._model
        wrapped = getattr(django_model, self.name)
        manager = wrapped.__get__(instance, owner)
        manager.__class__ = wrap_related_manager(manager.__class__)
        return manager


    def __set_name__(self, owner, name):
        self.name = name
        print('name', name)

#TODO cache

def wrap_related_manager(cls):
    class RelatedManager(cls):

        async def add(self, *objs):
            async with deferred.driver():
                print(cls.add.__get__(self))
                super().add(*objs)

    return RelatedManager



