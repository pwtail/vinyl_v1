from django.db.models import QuerySet

from vinyl.queryset import VinylQuerySet


def Await(obj):
    if isinstance(obj, QuerySet):
        return VinylQuerySet.__Await__(obj)
    return obj.__Await__()