"""Implements graph mutation functions."""

from collections import defaultdict
from collections.abc import Generator
from dataclasses import dataclass
from itertools import chain
from typing import Protocol, final

from rdflib import Graph
from rdflib.graph import _ObjectType
from rdflib.term import URIRef


@final
@dataclass(frozen=True)
class SubjectObjectQuery:
    """Query for the subject_object_dicts function."""

    typ: type[_ObjectType]
    predicates: tuple[URIRef, ...]


def subject_object_dicts(
    graph: Graph,
    *queries: SubjectObjectQuery,
) -> Generator[dict[URIRef, tuple[_ObjectType, ...]]]:
    """For each query, yield a dictionary { subject: list[objects] } matching the given predicates and being of the given typ."""
    all_predicates = {item for query in queries for item in query.predicates}

    pso = {p: defaultdict[URIRef, list[_ObjectType]](list) for p in all_predicates}
    for sub, pred, obj in sorted(graph):
        if not isinstance(sub, URIRef):
            continue
        if pred not in all_predicates or not isinstance(pred, URIRef):
            continue
        pso[pred][sub].append(obj)

    for query in queries:
        result_dict: defaultdict[URIRef, list[_ObjectType]] = defaultdict(list)
        for pred in query.predicates:
            for sub, values in pso[pred].items():
                result_dict[sub].extend(
                    value for value in values if isinstance(value, query.typ)
                )
        yield {k: tuple(v) for (k, v) in result_dict.items()}


class _SupportContainsURIRef(Protocol):
    def __contains__(self, item: URIRef) -> bool: ...


def used_namespaces(
    graph: Graph, always: _SupportContainsURIRef | None = None
) -> Generator[tuple[str, URIRef]]:
    """Yield all namespaces that are used in a graph."""
    iris = {
        iri
        for iri in chain(
            graph.subjects(),
            graph.predicates(),
            graph.objects(),
        )
        if isinstance(iri, URIRef)
    }

    always_include: _SupportContainsURIRef = set() if always is None else always

    return (
        (prefix, ns)
        for prefix, ns in graph.namespaces()
        if (ns in always_include) or any(iri.startswith(ns) for iri in iris)
    )
