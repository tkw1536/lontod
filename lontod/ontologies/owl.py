from .ontology import Ontology, subjects
from rdflib import Graph
from rdflib.namespace import (
    RDF,
    OWL,
)
from rdflib.util import guess_format
from pylode.profiles.ontpub import OntPub

# properties that are considered
_DEFINIENDA = {
    OWL.Class,
    OWL.Ontology,
    RDF.Property,
    OWL.ObjectProperty,
    OWL.DatatypeProperty,
    OWL.AnnotationProperty,
    OWL.FunctionalProperty,
}

_FORMAT_TO_MEDIA_TYPES_ = {
    'xml': 'application/rdf+xml',
    'n3': 'text/n3',
    'turtle': 'text/turtle',
    'nt': 'text/plain',
    'trig': 'application/trig',
    'json-ld': 'application/ld+json',
    'hext': 'application/x-ndjson', 
}

def OWLOntology(graph: Graph) -> Ontology:
    """ Returns a new OWL Ontology """

    # determine the URI of the ontology
    uri = None
    for s in graph.subjects(RDF.type, OWL.Ontology):
        uri = str(s)
    if uri is None:
        raise Exception('no defined owl ontology')
    
    # encode the ontology in all different formats
    types = [(media_type, graph.serialize(None, format)) for (format, media_type) in _FORMAT_TO_MEDIA_TYPES_.items()]
    types.append(('text/html', OntPub(graph).make_html().encode('utf-8')))
    
    return Ontology(
        uri=uri,
        encodings=dict(types),
        definienda=subjects(graph, _DEFINIENDA)
    )
