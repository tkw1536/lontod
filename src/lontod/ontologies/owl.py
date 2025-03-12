"""OWL Ontology Parsing"""

from typing import Generator, List, Tuple, Union, Optional

from dominate.tags import code, div, dom_tag, table, td, th, tr
from pylode.profiles.ontpub import OntPub
from rdflib import Graph
from rdflib.namespace import (
    OWL,
    RDF,
)

from .ontology import NoOntologyFound, Ontology

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
    "xml": "application/rdf+xml",
    "n3": "text/n3",
    "turtle": "text/turtle",
    "nt": "text/plain",
    "trig": "application/trig",
    "json-ld": "application/ld+json",
    "hext": "application/x-ndjson",
}


def owl_ontology(graph: Graph) -> Ontology:
    """Returns a new OWL Ontology"""

    # determine the URI of the ontology
    uri = None
    for s in graph.subjects(RDF.type, OWL.Ontology):
        uri = str(s)
    if uri is None:
        raise NoOntologyFound()

    # encode the ontology in all different formats
    types = [
        (media_type, _as_utf8(graph.serialize(None, format)))
        for (format, media_type) in _FORMAT_TO_MEDIA_TYPES_.items()
    ]

    # make html
    pub = OntPub(graph)
    types.append(("text/html", _as_utf8(pub.make_html())))

    return Ontology(
        uri=uri,
        encodings=dict(types),
        definienda=list(definienda_of(pub, uri)),
    )


def _as_utf8(value: Union[str, bytes]) -> bytes:
    if isinstance(value, str):
        return value.encode("utf-8")
    return value


def definienda_of(pub: OntPub, uri: str) -> Generator[Tuple[str, Optional[str]]]:
    """finds all (definiendum, fragment) identifiers in the given ontopub profile."""

    # This finds all definienda defined in the ontopub profile.
    #
    #   div > table > tr > (th|td) > code
    #
    # - the id of the outer div element must have an id (used as the fragment)
    # - the tr must have exactly two child elements
    # - the first one must say "IRI"
    # - the second one must contain the code element (text used as definiendum)

    yield (uri, None)

    for code_elem in all_tags(pub.doc.body):
        if not isinstance(code_elem, code):
            continue

        td_elem = code_elem.parent
        if not isinstance(td_elem, (td, th)):
            continue

        tr_elem = td_elem.parent
        if not isinstance(tr_elem, tr):
            continue

        children = child_tags(tr_elem)
        if (
            len(children) != 2
            or children[1] != td_elem
            or child_text(children[0]) != "IRI"
        ):
            continue

        table_elem = tr_elem.parent
        if not isinstance(table_elem, table):
            continue

        div_elem = table_elem.parent
        if not isinstance(div_elem, div):
            continue

        if "id" not in div_elem.attributes:
            continue

        yield (child_text(code_elem), div_elem.attributes["id"])


def child_text(root: dom_tag) -> str:
    """returns the concatenation of all children which are strings"""
    return "".join(filter(lambda x: isinstance(x, str), root.children))


def child_tags(root: dom_tag) -> List[dom_tag]:
    """Finds all children of root which are tags"""
    return list(filter(lambda x: isinstance(x, dom_tag), root.children))


def all_tags(root: dom_tag) -> Generator[dom_tag]:
    """yields all tags recursively"""

    # ignore non-tags!
    if not isinstance(root, dom_tag):
        return

    yield root
    for child in root.children:
        for tag in all_tags(child):
            yield tag
