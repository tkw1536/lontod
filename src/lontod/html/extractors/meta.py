"""loads information about background ontologies."""

# spellchecker:words RDFS onts

import contextlib
from collections.abc import Generator, Sequence
from functools import cached_property
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

from lontod.html.data.meta import MetaOntology, MetaProperty
from lontod.html.extractors._rdf import PROPS
from lontod.utils.cached import PickleCachedMeta
from lontod.utils.graph import SubjectObjectQuery, subject_object_dicts

from .core import iri_to_title

RDF_FOLDER = resources.files(__package__).joinpath("ontologies")


@final
class MetaExtractor(metaclass=PickleCachedMeta):
    """Holds information about the meta ontologies."""

    def __init__(self) -> None:
        """Create a new MetaOntologies object."""
        g = _MetaGraph()

        self.__types = g.types
        self.__titles = g.titles
        self.__props = g.props

    def __getitem__(self, iri: URIRef) -> MetaProperty:
        """Get information about a specific property."""
        return self.__props[iri]

    def types_of(self, iri: URIRef) -> Generator[URIRef]:
        """Iterate over the types of the given IRI."""
        with contextlib.suppress(KeyError):
            yield from self.__types[iri]

    def title_of(self, iri: URIRef) -> Literal | None:
        """Return the title of the given IRI, if it exists in the metadata ontology."""
        try:
            return self.__titles[iri][0]
        except KeyError:
            return None
        except IndexError:
            return None


logger = getLogger(__name__)


class _MetaGraph:
    """In-memory representation for the loaded meta ontologies graph."""

    def __init__(self) -> None:
        """Create the meta ontologies graph."""
        q = subject_object_dicts(
            self.g,
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
        self.types = cast("dict[URIRef,Sequence[URIRef]]", next(q))
        self.descriptions = cast("dict[URIRef,Sequence[Literal]]", next(q))
        self.titles = cast("dict[URIRef,Sequence[Literal]]", next(q))

    @cached_property
    def g(self) -> Graph:
        """Graph representing background ontologies."""
        g = Graph(bind_namespaces="core")

        for file in RDF_FOLDER.iterdir():
            if not file.is_file() or not file.name.endswith(".ttl"):
                continue
            logger.debug("parsing background ontology from %r", file)
            g.parse(None, file=cast("TextIO", file.open("r")), format="n3")

        return g

    @cached_property
    def ontologies(self) -> Generator[MetaOntology]:
        """Returns a dictionary of titles for ontologies."""
        for s in self.g.subjects(predicate=RDF.type, object=OWL.Ontology):
            if not isinstance(s, URIRef):
                continue

            try:
                yield MetaOntology(iri=s, titles=self.titles[s])
            except KeyError:
                continue

    @cached_property
    def props(self) -> dict[str, MetaProperty]:
        """Information about properties defined by ontologies."""
        return {iri: self.__prop_info(iri) for iri in PROPS}

    def __prop_info(self, prop: URIRef) -> MetaProperty:
        titles = self.titles.get(prop)
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
            descriptions=self.descriptions.get(prop) or (),
            ontologies=[ontology for ontology in self.ontologies if prop in ontology],
        )
