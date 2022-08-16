from __future__ import annotations
import typing

from django.db.models.sql.compiler import SQLCompiler


class QueryResult(typing.NamedTuple):
    compiler: SQLCompiler
    results: typing.Iterable

