"""OWL Ontology Parsing"""

from itertools import chain
from logging import Logger
from typing import Generator, List, Tuple

from bs4 import BeautifulSoup, Tag
from rdflib import Graph, Literal, Node
from rdflib.namespace import DCTERMS, OWL, PROF, RDF, SKOS, XSD

from lontod.html import OntPub

from ..utils.graph import restrict_languages, sanitize
from ..utils.strings import as_utf8
from .ontology import NoOntologyFound, Ontology
from .types import media_types


def owl_ontology(logger: Logger, graph: Graph, html_languages: List[str]) -> Ontology:
    """Returns a new OWL Ontology"""

    # determine the URI of the ontology
    uri = None
    for s in graph.subjects(RDF.type, OWL.Ontology):
        uri = str(s)
    if uri is None:
        raise NoOntologyFound()

    # encode the ontology in all different formats
    types = [
        (typ, as_utf8(graph.serialize(None, extension)))
        for (extension, typ) in media_types()
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
    result = OntPub(logger, graph).make_html()
    if not isinstance(result, (str, bytes)):
        raise AssertionError("OntPub did not return str or bytes")
    html = as_utf8(result)
    types.append(("text/html", html))

    return Ontology(
        uri=uri,
        alternate_uris=list(get_alternate_uris(graph)),
        encodings=dict(types),
        definienda=list(definienda_of(BeautifulSoup(html, "html.parser"))),
    )


def insert_fallback_title(g: Graph, *titles: Node) -> bool:
    """Inserts a fallback title for an ontology, and returns if one has been inserted"""

    uri = None
    for s in chain(
        g.subjects(RDF.type, OWL.Ontology),
        g.subjects(RDF.type, PROF.Profile),
        g.subjects(RDF.type, SKOS.ConceptScheme),
    ):
        uri = s

        # if we have some title, we don't need to add one!
        for _ in g.objects(s, DCTERMS.title):
            return False

        # insert all the titles
        for title in titles:
            g.add((uri, DCTERMS.title, title))
        return True

    raise AssertionError("no ontology found in graph")


def get_alternate_uris(g: Graph) -> Generator[str, None, None]:
    """gets the alternate URIS for a given graph"""
    for s in chain(
        g.subjects(RDF.type, OWL.Ontology),
        g.subjects(RDF.type, PROF.Profile),
        g.subjects(RDF.type, SKOS.ConceptScheme),
    ):
        for obj in g.objects(s, OWL.versionIRI):
            yield str(obj)

        return

    return


def definienda_of(
    html: BeautifulSoup,
) -> Generator[Tuple[str, str]]:
    """finds all (definiendum, fragment) identifiers in the given ontopub profile."""

    # This finds all definienda defined in the ontopub profile.
    #
    #   div > table > tr > (th|td) > code
    #
    # - the id of the outer div element must have an id (used as the fragment)
    # - the tr must have exactly two child elements
    # - the first one must say "IRI"
    # - the second one must contain the code element (text used as definiendum)

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
