"""OWL Ontology Parsing"""

from itertools import chain
from typing import Generator, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag
from pylode.profiles.ontpub import OntPub
from rdflib import Graph, Literal, Node
from rdflib.namespace import DCTERMS, OWL, PROF, RDF, SKOS, XSD

from ..utils.graph import restrict_languages, sanitize
from ..utils.strings import as_utf8
from .ontology import NoOntologyFound, Ontology

_FORMAT_TO_MEDIA_TYPES_ = {
    "xml": "application/rdf+xml",
    "n3": "text/n3",
    "turtle": "text/turtle",
    "nt": "text/plain",
    "trig": "application/trig",
    "json-ld": "application/ld+json",
    "hext": "application/x-ndjson",
}


def owl_ontology(graph: Graph, html_languages: List[str]) -> Ontology:
    """Returns a new OWL Ontology"""

    # determine the URI of the ontology
    uri = None
    for s in graph.subjects(RDF.type, OWL.Ontology):
        uri = str(s)
    if uri is None:
        raise NoOntologyFound()

    # encode the ontology in all different formats
    types = [
        (media_type, as_utf8(graph.serialize(None, format)))
        for (format, media_type) in _FORMAT_TO_MEDIA_TYPES_.items()
    ]

    # prepare graph for use in OntPub

    # remove all other languages
    if len(html_languages) > 0:
        restrict_languages(graph, html_languages)

    # make sure that there is a fallback title
    insert_fallback_title(graph, Literal("", datatype=XSD.string))

    # cleanup, to prevent at least some html injections!
    sanitize(graph)

    # make html
    html = as_utf8(OntPub(graph).make_html())
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
