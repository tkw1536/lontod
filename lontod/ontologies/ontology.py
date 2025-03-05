from dataclasses import dataclass
from rdflib import Graph
from rdflib.namespace import RDF
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

def subjects(graph: Graph, types: Iterable[str]) -> set[str]:
    """ Extracts all subjects of the given type from the graph """

    subjects = set()

    for tp in types:
        for s in graph.subjects(RDF.type, tp):
            subjects.add(str(s))
    
    return subjects