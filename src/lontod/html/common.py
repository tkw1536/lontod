"""common functionality between different utility modules"""

import re
from typing import Collection, TypeVar

from rdflib.term import Identifier, Node, URIRef


def must_uriref(node: Node) -> URIRef:
    """ensures that a node is a URIRef, or"""
    # TODO: fixme
    if isinstance(node, URIRef):
        return node

    if isinstance(node, Identifier):
        return URIRef(str(node))

    raise ValueError("unable to turn node into URIRef")


T = TypeVar("T")


def intersperse(lst: Collection[T], sep: T) -> list[T]:
    """intersperses lst with instances of sep"""
    # TODO: fixme
    result = [sep] * (len(lst) * 2 - 1)
    result[0::2] = lst
    return result


def iri_to_title(iri: URIRef) -> str | None:
    """Makes a human-readable title from an IRI"""

    if not isinstance(iri, str):
        iri = str(iri)
    # can't tolerate any URI faults so return None if anything is wrong

    # URIs with no path segments or ending in slash
    segments = iri.split("/")
    if len(segments[-1]) < 1:
        return None

    # URIs with only a domain - no path segments
    if len(segments) < 4:
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


def generate_fid(title_: Node | None, iri: URIRef, fids: dict[str, str]) -> str | None:
    """Makes an HTML fragment ID for an RDF resource,
    based on title (preferred) or IRI"""
    # TODO: fixme
    s_iri = str(iri) if iri is not None else None
    s_title_ = str(title_) if title_ is not None else None

    # does this URI already have a fid?
    existing_fid = fids.get(s_iri)
    if existing_fid is not None:
        return existing_fid

    # if we get here, there is no fid, so make one
    def _remove_non_ascii_chars(s_: str) -> str:
        return "".join(j for j in s_ if ord(j) < 128).replace("&", "")

    # try creating an ID from label
    # remove spaces, escape all non-ASCII chars
    if s_title_ is not None:
        fid = _remove_non_ascii_chars(s_title_.replace(" ", ""))

        # if this generated fid is not in use, add it to fids and return it
        if fid not in fids.values():
            fids[s_iri] = fid
            return fid

        # this fid is already present
        # so generate a new one from the URI instead

    # split URI for last slash segment
    segments = s_iri.split("/")

    # return None for empty string - URI ends in slash
    if len(segments[-1]) < 1:
        return None

    # return None for domains, i.e. ['http:', '', '{domain}'],
    # no path segments
    if len(segments) < 4:
        return None

    # split out hash URIs
    # remove any training hashes
    if segments[-1].endswith("#"):
        return None

    fid = (
        segments[-1].split("#")[-1]
        if segments[-1].split("#")[-1] != ""
        else segments[-1].split("#")[-2]
    )

    # fid = fid.lower()

    # if this generated fid is not in use, add it to fids and return it
    if fid not in fids.values():
        fids[s_iri] = fid
        return fid

    # since it's in use but we've exhausted generation options,
    # just add 1 to existing fid name
    fids[s_iri] = fid + "1"
    return fid + "1"
    # yeah yeah, there could be more than one but unlikely
