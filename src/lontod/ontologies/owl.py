"""OWL Ontology Parsing"""

from typing import Generator, Tuple, Union, Optional

from pylode.profiles.ontpub import OntPub
from rdflib import Graph, Literal, Node
from rdflib.namespace import OWL, RDF, DCTERMS, PROF, SKOS, XSD
from itertools import chain

from bs4 import BeautifulSoup, Tag

from .ontology import NoOntologyFound, Ontology
from ..utils.graph import only_object_lang, sanitize


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


def owl_ontology(graph: Graph, html_language: Optional[str] = None) -> Ontology:
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

    # prepare graph for use in OntPub

    # remove all other languages    
    if isinstance(html_language, str):
        only_object_lang(graph, html_language)

    # make sure
    insert_fallback_title(
        graph, Literal("", datatype=XSD.string)
    )

    # cleanup, to prevent at least some html injections!
    sanitize(graph)

    # make html
    html = _as_utf8(OntPub(graph).make_html())
    types.append(("text/html", html))

    return Ontology(
        uri=uri,
        encodings=dict(types),
        definienda=list(definienda_of(BeautifulSoup(html, "html.parser"), uri)),
    )


def insert_fallback_title(g: Graph, *titles: Node) -> None:
    """Inserts a fallback title for an ontology if none is found"""

    uri = None
    for s in chain(
        g.subjects(RDF.type, OWL.Ontology),
        g.subjects(RDF.type, PROF.Profile),
        g.subjects(RDF.type, SKOS.ConceptScheme),
    ):
        uri = s

        # if we have some title, we don't need to add one!
        for _ in g.objects(s, DCTERMS.title):
            return

        # insert all the titles
        for title in titles:
            g.add((uri, DCTERMS.title, title))
        return


def _as_utf8(value: Union[str, bytes]) -> bytes:
    """Turns a value into a utf-8 encoded set of bytes, unless it already is"""
    if isinstance(value, str):
        return value.encode("utf-8")
    return value


def definienda_of(
    html: BeautifulSoup, uri: str
) -> Generator[Tuple[str, Optional[str]]]:
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

    for code in html.find_all("code"):
        td_elem = code.parent
        if td_elem is None or not _is_tag(td_elem, "td", "th"):
            continue

        tr_elem = td_elem.parent
        if tr_elem is None or not _is_tag(tr_elem, "tr"):
            continue

        children = [c for c in tr_elem.children if isinstance(c, Tag)]
        if (
            len(children) != 2
            or children[1] != td_elem
            or children[0].getText() != "IRI"
        ):
            continue

        table_elem = tr_elem.parent
        if table_elem is None or not _is_tag(table_elem, "table"):
            continue

        div_elem = table_elem.parent
        if div_elem is None or not _is_tag(div_elem, "div"):
            continue

        fragment_id = div_elem.get("id")
        if not isinstance(fragment_id, str):
            continue

        yield (code.getText(), fragment_id)


def _is_tag(tag: Tag, *names: str) -> bool:
    """Checks if the given tag corresponds to any of the given tag names"""
    t = tag.name.lower()
    for n in names:
        if n.lower() == t:
            return True
    return False
