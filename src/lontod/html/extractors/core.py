"""Extractor functions shared between different utilities."""

import re

from rdflib.term import URIRef


def iri_to_title(iri: URIRef) -> str | None:
    """Make a human-readable title from an IRI."""
    if not isinstance(iri, str):
        iri = str(iri)
    # can't tolerate any URI faults so return None if anything is wrong

    # URIs with no path segments or ending in slash
    segments = iri.split("/")
    if len(segments[-1]) < 1:
        return None

    # URIs with only a domain - no path segments
    if len(segments) < 4:  # noqa: PLR2004
        return None

    # URIs ending in hash
    if segments[-1].endswith("#"):
        return None

    id_part = (
        segments[-1].split("#")[-1]
        if segments[-1].split("#")[-1] != ""
        else segments[-1].split("#")[-2]
    )

    # split CamelCase
    # title case if the first char is uppercase (likely a Class)
    # else lower (property/Named Individual)
    words = re.split(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", id_part)
    if words[0][0].isupper():
        return " ".join(words).title()
    return " ".join(words).lower()
