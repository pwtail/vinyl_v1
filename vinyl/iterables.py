
from django.db.models.query import ModelIterable, FlatValuesListIterable, NamedValuesListIterable, ValuesListIterable, ValuesIterable


class AwaitMixin:
    """Iterable that yields a model instance for each row."""

    async def __Await__(self):
        compiler = self.queryset.query.get_compiler(using=self.queryset.db)
        await(compiler)
        return self

    def __await__(self):
        return self.__Await__().__await__()


class ModelIterable(AwaitMixin, ModelIterable):
    pass


class FlatValuesListIterable(AwaitMixin, FlatValuesListIterable):
    pass


class NamedValuesListIterable(AwaitMixin, NamedValuesListIterable):
    pass


class ValuesListIterable(AwaitMixin, ValuesListIterable):
    pass


class ValuesIterable(AwaitMixin, ValuesIterable):
    pass
