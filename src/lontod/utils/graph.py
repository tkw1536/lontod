from rdflib import Graph, Literal
from typing import Optional
from html_sanitizer import Sanitizer # type: ignore


def sanitize(g: Graph) -> None:
    """Sanitizes a graph, cleanup up triples as needed"""

    cleaned = Graph()

    for (s, p, o) in g:
        if not isinstance(o, Literal):
            continue

        co = _sanitize_literal(o)
        if co is None:
            continue

        # remove the triple and add to buffer to add
        g.remove((s, p, o))
        cleaned.add((s, p, co))

    # add back all the cleaned triples!
    for (
        s,
        p,
        o,
    ) in cleaned:
        g.add((s, p, o))


sanitizer = Sanitizer({"keep_typographic_whitespace": True})

def _sanitize_literal(o: Literal) -> Optional[Literal]:
    # make sure we have a string value
    # and if we don't cast to it!
    o_value = o.value
    if not isinstance(o_value, str):
        o_value = str(o_value)

    value = sanitizer.sanitize(o_value)
    if value == o_value:  # nothing changed
        return None

    return Literal(value, datatype=o.datatype, lang=o.language)


def only_object_lang(g: Graph, lang: str) -> None:
    """Restricts a graph to objects of a specific language.

    Args:
        g (Graph): Graph to copy
        lang (str): Language to limit object to
    """

    for s, p, o in g:
        if not isinstance(o, Literal):
            continue
        if o.language is None or o.language == lang:
            continue
        g.remove((s, p, o))
