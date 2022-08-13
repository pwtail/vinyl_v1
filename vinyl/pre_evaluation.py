from __future__ import annotations
import threading
import typing
from contextlib import contextmanager

from django.db.models import QuerySet
from django.db.models.sql.compiler import SQLCompiler

tlocal = threading.local()
tlocal.value = None


@contextmanager
def pre_evaluate(*, queryset, compiler, results):
    tlocal.value = QuerySetResult(qs=queryset, compiler=compiler, results=results)
    try:
        yield tlocal.value
    finally:
        tlocal.value = None


class QuerySetResult(typing.NamedTuple):
    qs: QuerySet
    compiler: SQLCompiler
    results: typing.Iterable

    @classmethod
    def get(cls) -> QuerySetResult:
        return tlocal.value