"""Implements graph mutation functions"""

from typing import (
    Any,
    Dict,
    Generator,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeGuard,
)

from html_sanitizer.sanitizer import Sanitizer, sanitize_href  # type: ignore
from rdflib import Graph, Literal
from rdflib.graph import _PredicateType, _SubjectType, _TripleType

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


def sanitize(g: Graph, settings: Optional[Dict[str, Any]] = None) -> None:
    """Sanitizes a graph by removing any dangerous html from it.

    Args:
        g (Graph): Graph to be sanitized
        settings (Optional[Dict[str,Any]], optional): Settings for sanitization to be passed to the 'html_sanitizer' module. Defaults to None.
    """
    sanitizer = Sanitizer(settings if settings is not None else _SANITIZE_SETTINGS)

    cleaned_edges: List[_TripleType] = []
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
            (s, p, Literal(c_o_value, datatype=o.datatype, lang=o.language))
        )
        g.remove((s, p, o))

    # add back the cleaned edges
    for edge in cleaned_edges:
        g.add(edge)


def restrict_languages(g: Graph, preferences: Optional[Sequence[str]] = None) -> None:
    """Restricts the available internationalized object values per (subject, predicate) pair in the graph.
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
    offers: set[Optional[str]], preferences: Optional[Sequence[str]]
) -> Optional[str]:
    """Picks a language from the given set of offers (or None).

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
    def is_str(s: Optional[str]) -> TypeGuard[str]:
        return s is not None

    return min(filter(is_str, offers))


def _subject_predicates(g: Graph) -> Generator[Tuple[_SubjectType, _PredicateType]]:
    """Yields all unique (subject, predicate) pairs for the given graph"""
    for s in g.subjects(unique=True):
        for p in g.predicates(subject=s, unique=True):
            yield (s, p)
