"""OWL Ontology Parsing."""

from collections.abc import Generator, Sequence
from itertools import chain
from logging import Logger

from rdflib import Graph
from rdflib.namespace import OWL, PROF, RDF, SKOS

from lontod.utils.strings import as_utf8

from .data import RenderContext
from .extractors import OntologyExtractor
from .ontology import NoOntologyFoundError, Ontology
from .types import media_types


def owl_ontology(
    logger: Logger, graph: Graph, html_languages: Sequence[str | None]
) -> Ontology:
    """Return a new OWL Ontology."""
    _ = logger  # TODO: mark argument as used for now

    # determine the URI of the ontology
    uri = None
    for s in graph.subjects(RDF.type, OWL.Ontology):
        uri = str(s)
    if uri is None:
        raise NoOntologyFoundError

    # encode the ontology in all different formats
    types = [
        (typ, as_utf8(graph.serialize(None, extension)))
        for (extension, typ) in media_types()
    ]

    # create an ontology and a render context to go along with it
    ont = OntologyExtractor(graph)()
    ctx = RenderContext(ont, html_languages)

    # render it as html
    html = as_utf8(ont.to_html(ctx).render())
    types.append(("text/html", html))

    # extract the definienda
    definienda = [(str(defi.iri), ctx.fragment(defi.iri)) for defi in ont]

    return Ontology(
        uri=uri,
        alternate_uris=list(get_alternate_uris(graph)),
        encodings=dict(types),
        definienda=definienda,
    )


def get_alternate_uris(g: Graph) -> Generator[str]:
    """Get the alternate URIS for a given graph."""
    for s in chain(
        g.subjects(RDF.type, OWL.Ontology),
        g.subjects(RDF.type, PROF.Profile),
        g.subjects(RDF.type, SKOS.ConceptScheme),
    ):
        for obj in g.objects(s, OWL.versionIRI):
            yield str(obj)

        return

    return
