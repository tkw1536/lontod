"""Basic ontology definitions and utility functions"""

from dataclasses import dataclass
from os.path import basename, splitext
from typing import Iterable, Optional

from rdflib import Graph
from rdflib.namespace import RDF


@dataclass
class Ontology:
    """Represents an ontology that can be indexed"""

    # URI Identifier of this ontology
    uri: str

    # map from media type to content of ontology
    encodings: dict[str, bytes]

    # list of (definiendum, fragment)
    definienda: list[[str, Optional[str]]]


def slug_from_path(path: str) -> str:
    """Given a relative or absolute pathname, return a slug for the given ontology"""

    base, _ = splitext(basename(path))
    return base


def subjects(graph: Graph, types: Iterable[str]) -> set[str]:
    """Extracts all subjects of the given type from the graph"""

    uris = set()

    for tp in types:
        for s in graph.subjects(RDF.type, tp):
            uris.add(str(s))

    return uris
