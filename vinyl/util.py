from django.db.models import QuerySet


def Await(obj):
    if isinstance(obj, QuerySet):
        from vinyl.queryset import VinylQuerySet
        return VinylQuerySet.__Await__(obj)
    return obj.__Await__()