"""loads information about background ontologies."""

# spellchecker:words RDFS onts

from collections.abc import Generator, Sequence
from importlib import resources
from logging import getLogger
from typing import TextIO, cast, final

from rdflib import Graph
from rdflib.namespace import (
    DC,
    DCTERMS,
    OWL,
    RDF,
    RDFS,
    SDO,
    SKOS,
)
from rdflib.term import Literal, URIRef

from lontod.html.data.meta import MetaOntologies, MetaOntology, MetaProperty
from lontod.html.data.rdf import PROPS
from lontod.utils.cached import PickleCachedMeta
from lontod.utils.graph import SubjectObjectQuery, subject_object_dicts

from .core import iri_to_title

RDF_FOLDER = resources.files(__package__).joinpath("meta_rdf")

logger = getLogger(__name__)


@final
class MetaExtractor(metaclass=PickleCachedMeta):
    """In-memory representation for the loaded meta ontologies graph."""

    def __init__(self) -> None:
        """Create the meta ontologies graph."""
        self.__g = self.__init_g()

        q = subject_object_dicts(
            self.__g,
            SubjectObjectQuery(
                typ=URIRef,
                predicates=(RDF.type,),
            ),
            SubjectObjectQuery(
                typ=Literal,
                predicates=(
                    DC.description,
                    RDFS.comment,
                    SKOS.definition,
                    SDO.description,
                    DCTERMS.description,
                ),
            ),
            SubjectObjectQuery(
                typ=Literal,
                predicates=(
                    DC.title,
                    RDFS.label,
                    SKOS.prefLabel,
                    SDO.name,
                    DCTERMS.title,
                ),
            ),
        )
        self.__types = cast("dict[URIRef,Sequence[URIRef]]", next(q))
        self.__descriptions = cast("dict[URIRef,Sequence[Literal]]", next(q))
        self.__titles = cast("dict[URIRef,Sequence[Literal]]", next(q))

        self.__ontologies = list(self.__init_ontologies())
        self.__props = self.__init_props()

    def __call__(self) -> MetaOntologies:
        """Extract information about the meta ontologies."""
        return MetaOntologies(
            types=self.__types, titles=self.__titles, props=self.__props
        )

    def __init_g(self) -> Graph:
        """Graph representing background ontologies."""
        g = Graph(bind_namespaces="core")

        for file in RDF_FOLDER.iterdir():
            if not file.is_file() or not file.name.endswith(".ttl"):
                continue
            logger.debug("parsing background ontology from %r", file)
            g.parse(None, file=cast("TextIO", file.open("r")), format="n3")

        return g

    def __init_ontologies(self) -> Generator[MetaOntology]:
        for s in self.__g.subjects(predicate=RDF.type, object=OWL.Ontology):
            if not isinstance(s, URIRef):
                continue

            try:
                yield MetaOntology(iri=s, titles=self.__titles[s])
            except KeyError:
                continue

    def __init_props(self) -> dict[str, MetaProperty]:
        return {iri: self.__prop_info(iri) for iri in PROPS}

    def __prop_info(self, prop: URIRef) -> MetaProperty:
        titles = self.__titles.get(prop)
        if titles is None or len(titles) == 0:
            auto_title = iri_to_title(prop)
            if auto_title is None:
                msg = f"unable to generate title for IRI for property {prop!r}"
                raise AssertionError(
                    msg,
                )
            titles = [Literal(auto_title)]

        return MetaProperty(
            iri=prop,
            titles=titles,
            descriptions=self.__descriptions.get(prop) or (),
            ontologies=[ontology for ontology in self.__ontologies if prop in ontology],
        )
