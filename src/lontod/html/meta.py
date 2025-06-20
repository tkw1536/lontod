"""loads information about background ontologies."""

# spellchecker:words RDFS onts

import contextlib
from collections import defaultdict
from collections.abc import Generator, Sequence
from functools import cached_property
from importlib import resources
from logging import getLogger
from typing import TextIO, TypeVar, cast, final

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
from rdflib.term import Literal, Node, URIRef

from lontod.utils.cached import PickleCachedMeta

from .common import iri_to_title
from .data import MetaOntology, MetaProperty
from .rdf_elements import PROPS

RDF_FOLDER = resources.files(__package__).joinpath("ontologies")


@final
class MetaOntologies(metaclass=PickleCachedMeta):
    """Holds information about the meta ontologies."""

    def __init__(self) -> None:
        """Create a new MetaOntologies object."""
        g = _MetaOntologiesGraph()

        self.__types = g.types
        self.__titles = g.titles
        self.__props = g.props

    def __getitem__(self, uri: URIRef) -> MetaProperty:
        """Get information about a specific property."""
        return self.__props[uri]

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


T = TypeVar("T", bound=Node)

logger = getLogger("lontod.ontology.background")


class _MetaOntologiesGraph:
    """In-memory representation for the loaded meta ontologies graph."""

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
    def types(self) -> dict[URIRef, Sequence[URIRef]]:
        """Returns a dictionary holding all types for all objects."""
        return self.__subject_object_dict((RDF.type,), URIRef)

    @cached_property
    def descriptions(self) -> dict[URIRef, Sequence[Literal]]:
        """Returns a dictionary holding the descriptions of all objects."""
        return self.__subject_object_dict(
            (
                DC.description,
                RDFS.comment,
                SKOS.definition,
                SDO.description,
                DCTERMS.description,
            ),
            Literal,
        )

    @cached_property
    def titles(self) -> dict[URIRef, Sequence[Literal]]:
        """Returns a dictionary holding the titles of all objects."""
        return self.__subject_object_dict(
            (
                DC.title,
                RDFS.label,
                SKOS.prefLabel,
                SDO.name,
                DCTERMS.title,
            ),
            Literal,
        )

    @cached_property
    def ontologies(self) -> Generator[MetaOntology]:
        """Returns a dictionary of titles for ontologies."""
        for s in self.g.subjects(predicate=RDF.type, object=OWL.Ontology):
            if not isinstance(s, URIRef):
                continue

            try:
                yield MetaOntology(uri=s, titles=self.titles[s])
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
            uri=prop,
            titles=titles,
            descriptions=self.descriptions.get(prop) or (),
            ontologies=[ontology for ontology in self.ontologies if prop in ontology],
        )

    def __subject_object_dict(
        self,
        predicates: Sequence[URIRef],
        typ: type[T],
    ) -> dict[URIRef, Sequence[T]]:
        """Build a dictionary { subject: list[objects] } with the given predicates."""
        so_dict = defaultdict[URIRef, list[T]](list)

        for predicate in predicates:
            for sub, obj in self.g.subject_objects(predicate):
                if not isinstance(sub, URIRef):
                    continue
                if not isinstance(obj, typ):
                    continue
                so_dict[sub].append(obj)

        return dict(so_dict)
