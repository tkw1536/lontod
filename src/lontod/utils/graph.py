"""Implements graph mutation functions."""

from collections import defaultdict
from collections.abc import Generator, Sequence
from dataclasses import dataclass
from typing import (
    Any,
    TypeGuard,
)

from html_sanitizer.sanitizer import (
    Sanitizer,
    sanitize_href,
)
from rdflib import Graph
from rdflib.graph import _ObjectType, _PredicateType, _SubjectType, _TripleType
from rdflib.term import Literal, URIRef

_SANITIZE_SETTINGS = {
    "tags": [
        "a",
        "b",
        "br",
        "em",
        "h1",
        "h2",
        "h3",
        "hr",
        "i",
        "li",
        "ol",
        "p",
        "strong",
        "sub",
        "sup",
        "ul",
    ],
    "attributes": {"a": ("href", "name", "target", "title", "rel")},
    "empty": {"hr", "a", "br"},
    "separate": {"a", "p", "li"},
    "whitespace": {"br"},
    "keep_typographic_whitespace": True,
    "add_nofollow": False,
    "autolink": False,
    "sanitize_href": sanitize_href,
    "element_preprocessors": [],
    "element_postprocessors": [],
}


def sanitize(g: Graph, settings: dict[str, Any] | None = None) -> None:
    """Sanitizes a graph by removing any dangerous html from it.

    Args:
        g (Graph): Graph to be sanitized
        settings (Optional[Dict[str,Any]], optional): Settings for sanitization to be passed to the 'html_sanitizer' module. Defaults to None.

    """
    sanitizer = Sanitizer(settings if settings is not None else _SANITIZE_SETTINGS)

    cleaned_edges: list[_TripleType] = []
    for s, p, o in g:
        if not isinstance(o, Literal):
            continue

        # ensure that o_value is a string
        o_value = o.value
        if not isinstance(o_value, str):
            o_value = str(o_value)

        # sanitize the value
        c_o_value = sanitizer.sanitize(o_value)
        if c_o_value == o_value:
            continue

        # add a cleaned edge
        cleaned_edges.append(
            (s, p, Literal(c_o_value, datatype=o.datatype, lang=o.language)),
        )
        g.remove((s, p, o))

    # add back the cleaned edges
    for edge in cleaned_edges:
        g.add(edge)


def restrict_languages(g: Graph, preferences: Sequence[str] | None = None) -> None:
    """Restrict languages in a graph.

    Restrict the available internationalized object values per (subject, predicate) pair in the graph.
    In particular, it picks all values that are of the first available language in preferences, or the
    alphabetically first language if None matches.

    Args:
        g (Graph): _description_
        preferences (Optional[List[str]], optional): _description_. Defaults to None.

    """
    for s, p in _subject_predicates(g):
        # find the languages for the given (subject, predicate) triples and pick a preference
        langs = [
            o.language
            for o in g.objects(subject=s, predicate=p)
            if isinstance(o, Literal)
        ]
        choice = _pick_language(set(langs), preferences)

        # no matching language choice
        if choice is None:
            continue

        for o in g.objects(subject=s, predicate=p):
            if not isinstance(o, Literal):
                continue

            if o.language == choice:
                continue
            g.remove((s, p, o))


def _pick_language(
    offers: set[str | None],
    preferences: Sequence[str] | None,
) -> str | None:
    """Pick a language from the given set of offers (or None).

    Args:
        offers (set[Optional[str]]): Set of available languages.
        preferences (Optional[Sequence[str]]): Sequence of preferred languages, or None.

    Returns:
        Optional[str]: A language from offers, or None if no languages are available.

    """
    # easy case: no languages available
    if len(offers) == 0 or (len(offers) == 1 and None in offers):
        return None

    # iterate over the preferences in order, and if there is one use it!
    for lang in preferences if preferences is not None else []:
        if lang in offers:
            return lang

    # pick the 'first' of the available languages
    def is_str(s: str | None) -> TypeGuard[str]:
        return s is not None

    return min(filter(is_str, offers))


def _subject_predicates(g: Graph) -> Generator[tuple[_SubjectType, _PredicateType]]:
    """Yield all unique (subject, predicate) pairs for the given graph."""
    for s in g.subjects(unique=True):
        for p in g.predicates(subject=s, unique=True):
            yield (s, p)


@dataclass
class SubjectObjectQuery:
    """Query for the subject_object_dicts function."""

    typ: type[_ObjectType]
    predicates: Sequence[URIRef]


def subject_object_dicts(
    graph: Graph,
    *queries: SubjectObjectQuery,
) -> Generator[dict[URIRef, Sequence[_ObjectType]]]:
    """For each query, yield a dictionary { subject: list[objects] } matching the given predicates and being of the given typ."""
    all_predicates = {item for query in queries for item in query.predicates}

    pso = {p: defaultdict[URIRef, list[_ObjectType]](list) for p in all_predicates}
    for sub, pred, obj in graph:
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
        yield dict(result_dict)
