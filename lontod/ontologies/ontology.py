from dataclasses import dataclass
from rdflib import Graph
from rdflib.namespace import RDF
from os.path import basename, splitext
from typing import Iterable

@dataclass
class Ontology:
    """ Represents an ontology that can be index"""

    # URI Identifier of this ontology
    uri: str

    # map from media type to content of ontology
    encodings: dict[str,bytes]

    # set of urls defined by this ontology
    definienda: set[str]

def slug_from_path(path: str) -> str:
    """ Given a relative or absolute pathname, return a slug for the given ontology """
    
    base, _ = splitext(basename(path))
    return base
    

def subjects(graph: Graph, types: Iterable[str]) -> set[str]:
    """ Extracts all subjects of the given type from the graph """

    subjects = set()

    for tp in types:
        for s in graph.subjects(RDF.type, tp):
            subjects.add(str(s))
    
    return subjects