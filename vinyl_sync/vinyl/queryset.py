from django.db import NotSupportedError, connections, IntegrityError
from django.db.models import QuerySet, Model
from django.db.models.query import MAX_GET_RESULTS
from django.db.models.utils import resolve_callables

from vinyl import iterables
from vinyl.deferred import deferred
from vinyl.flags import is_async, use_vinyl
from vinyl.prefetch import prefetch_related_objects
from vinyl.query import VinylQuery


class VinylQuerySet(QuerySet):

    # almost exact copy, except for the statement
    def get(self, *args, **kwargs):
        if self.query.combinator and (args or kwargs):
            raise NotSupportedError(
                "Calling QuerySet.get(...) with filters after %s() is not "
                "supported." % self.query.combinator
            )
        clone = self._chain() if self.query.combinator else self.filter(*args, **kwargs)
        if self.query.can_filter() and not self.query.distinct_fields:
            clone = clone.order_by()
        limit = None
        if (
            not clone.query.select_for_update
            or connections[clone.db].features.supports_select_for_update_with_limit
        ):
            limit = MAX_GET_RESULTS
            clone.query.set_limits(high=limit)
        Await(clone)
        num = len(clone)
        if num == 1:
            return clone._result_cache[0]
        if not num:
            raise self.model.DoesNotExist(
                "%s matching query does not exist." % self.model._meta.object_name
            )
        raise self.model.MultipleObjectsReturned(
            "get() returned more than one %s -- it returned %s!"
            % (
                self.model._meta.object_name,
                num if not limit or num < limit else "more than %s" % (limit - 1),
            )
        )

    @classmethod
    def clone(cls, qs):
        #FIXME
        query = VinylQuery.convert(qs.query)
        c = cls(
            model=query.model,
            query=query,
            using=qs._db,
            hints=qs._hints,
        )
        c._sticky_filter = qs._sticky_filter
        c._for_write = qs._for_write
        c._prefetch_related_lookups = qs._prefetch_related_lookups[:]
        c._known_related_objects = qs._known_related_objects
        c._iterable_class = qs._iterable_class
        c._fields = qs._fields
        return c

    def __init__(self, model=None, query=None, using=None, hints=None):
        assert model

        # query = VinylQuery.convert(query)
        from vinyl.model import VinylModel
        if not issubclass(model, VinylModel):
            assert issubclass(model, Model)
            model = model.vinyl_model
        query = query or VinylQuery(model)
        super().__init__(model=model, query=query, using=using, hints=hints)

    def __await__(self):
        return self.__Await__().__await__()

    def __aiter__(self):
        return self._aiter()

    if is_async():
        def __iter__(self):
            yield from self._result_cache
    else:
        __iter__ = __aiter__

    def _aiter(self):
        Await(self)
        for item in self._result_cache:
            yield item

    @use_vinyl()
    def __Await__(self):
        if self._result_cache is None:
            iterable_class = getattr(iterables, self._iterable_class.__name__)
            self._result_cache = list(Await(iterable_class(self)))
        if self._prefetch_related_lookups and not self._prefetch_done:
            self._prefetch_related_objects()
        return self._result_cache

    def _fetch_all(self):
        if not is_async():
            self.__Await__()
        # no prefetch related

    def _prefetch_related_objects(self):
        prefetch_related_objects(self._result_cache, *self._prefetch_related_lookups)
        self._prefetch_done = True

    def prefetch(self, *args, **kw):
        return self.prefetch_related(*args, **kw)

    def get_or_none(self):
        try:
            return self.get()
        except self.model.DoesNotExist:
            return None

    def delete(self):
        # TODO model ??
        Await(self)
        with deferred():
            super().delete()

    def insert(self, using=None, **kwargs):
        instance = self.model(**kwargs)
        instance.insert(using=using)
        return instance

    #exact copy + await
    def first(self):
        """Return the first object of a query or None if no match is found."""
        if self.ordered:
            queryset = self
        else:
            self._check_ordering_first_last_queryset_aggregation(method="first")
            queryset = self.order_by("pk")
        for obj in Await(queryset[:1]):
            return obj

    #exact copy + await
    def last(self):
        """Return the last object of a query or None if no match is found."""
        if self.ordered:
            queryset = self.reverse()
        else:
            self._check_ordering_first_last_queryset_aggregation(method="last")
            queryset = self.order_by("-pk")
        for obj in Await(queryset[:1]):
            return obj

    def update(self, **kwargs):
        with deferred():
            super().update(**kwargs)

    #TODO transaction
    def get_or_create(self, defaults=None, **kwargs):
        """
        Look up an object with the given kwargs, creating one if necessary.
        Return a tuple of (object, created), where created is a boolean
        specifying whether an object was created.
        """
        # The get() needs to be targeted at the write database in order
        # to avoid potential transaction consistency problems.
        self._for_write = True
        try:
            return (self.get(**kwargs)), False
        except self.model.DoesNotExist:
            params = self._extract_model_params(defaults, **kwargs)
            # Try to create an object using passed params.
            try:
                params = dict(resolve_callables(params))
                return (self.create(**params)), True
            except IntegrityError:
                try:
                    return (self.get(**kwargs)), False
                except self.model.DoesNotExist:
                    pass
                raise

    def create(self, **kwargs):
        """
        Create a new object with the given kwargs, saving it to the database
        and returning the created object.
        """
        obj = self.model(**kwargs)
        obj.save(force_insert=True, using=self._db)
        return obj
