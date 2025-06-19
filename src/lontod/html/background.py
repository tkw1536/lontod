"""loads information about background ontologies"""

# spellchecker:words RDFS onts

from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property
from importlib import resources
from logging import getLogger
from typing import Generator, Sequence, TextIO, TypeVar, cast, final

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

from ..utils.cached import PickleCachedMeta
from .common import iri_to_title
from .rdf_elements import PROPS

RDF_FOLDER = resources.files(__package__).joinpath("ontologies")


@dataclass
class PropInfo:
    """Human-readable information about a specific property"""

    # title of the property
    title: str

    # description of the property
    description: str | None

    # ontology title
    ont_title: str | None


@final
class BackgroundOntologies(metaclass=PickleCachedMeta):
    """Holds information about background ontologies"""

    def __init__(self) -> None:
        g = _BackgroundOntologyGraph()

        self.__types = g.types
        self.__titles = g.titles
        self.__descriptions = g.descriptions
        self.__props = g.props

    def __getitem__(self, uri: URIRef) -> PropInfo:
        """gets information about a specific property"""

        return self.__props[uri]

    def types_of(self, iri: URIRef) -> Generator[URIRef, None, None]:
        """Iterates over the types of the given IRI"""
        try:
            yield from self.__types[iri]
        except KeyError:
            pass

    def titles_of(self, iri: URIRef) -> Generator[Literal, None, None]:
        """Returns the title of the given URI"""

        try:
            yield from self.__titles[iri]
        except KeyError:
            pass

    def title_of(self, iri: URIRef) -> Literal | None:
        """Like titles_of, but returns on the first title"""

        try:
            return self.__titles[iri][0]
        except KeyError:
            return None
        except IndexError:
            return None

    def descriptions_of(self, iri: URIRef) -> Generator[Literal, None, None]:
        """Yields all descriptions of the given iri"""

        try:
            yield from self.__descriptions[iri]
        except KeyError:
            pass

    def description_of(self, iri: URIRef) -> Literal | None:
        """Like descriptions_of, but returns only the first description"""

        try:
            return self.__descriptions[iri][0]
        except KeyError:
            return None
        except IndexError:
            return None


T = TypeVar("T", bound=Node)

logger = getLogger("lontod.ontology.background")


class _BackgroundOntologyGraph:
    """An in-memory loaded background ontology graph"""

    @cached_property
    def g(self) -> Graph:
        """graph representing background ontologies"""

        g = Graph(bind_namespaces="core")

        for file in RDF_FOLDER.iterdir():
            if not file.is_file() or not file.name.endswith(".ttl"):
                continue
            logger.debug("parsing background ontology from %r", file)
            g.parse(None, file=cast(TextIO, file.open("r")), format="n3")

        return g

    @cached_property
    def types(self) -> dict[URIRef, list[URIRef]]:
        """returns a dictionary holding all types for all objects"""

        return self.__subject_object_dict((RDF.type,), URIRef)

    @cached_property
    def descriptions(self) -> dict[URIRef, list[Literal]]:
        """returns a dictionary holding the descriptions of all objects"""

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
    def titles(self) -> dict[URIRef, list[Literal]]:
        """returns a dictionary holding the titles of all objects"""

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
    def ontology_titles(self) -> dict[URIRef, str]:
        """returns a dictionary of titles for ontologies"""
        ont_titles = {}
        for s in self.g.subjects(predicate=RDF.type, object=OWL.Ontology):
            if not isinstance(s, URIRef):
                continue

            try:
                titles = self.titles[s]
                if len(titles) > 1:
                    logger.debug("multiple titles for %s: %r", s, titles)
                ont_titles[s] = str(self.titles[s][0].value)
            except KeyError:
                continue

        return ont_titles

    @cached_property
    def props(self) -> dict[str, PropInfo]:
        """Information about properties defined by ontologies"""

        return {iri: self.__prop_info(iri) for iri in PROPS}

    def __prop_info(self, prop: URIRef) -> PropInfo:
        title: str
        title_lits = self.titles.get(prop)
        if title_lits is not None and len(title_lits) > 0:
            if len(title_lits) > 1:
                logger.debug("multiple titles for %s: %r", prop, title_lits)
            title = str(title_lits[0].value)
        else:
            auto_title = iri_to_title(prop)
            if auto_title is None:
                raise AssertionError(
                    f"unable to generate title for IRI for property {prop!r}"
                )
            title = auto_title

        description: str | None = None
        description_lits = self.descriptions.get(prop)
        if description_lits is not None and len(description_lits) > 0:
            if len(description_lits) > 1:
                logger.debug("multiple descriptions for %s: %r", prop, description_lits)
            description = str(description_lits[0].value)

        ont_titles: list[str] = []
        for k, v in self.ontology_titles.items():
            if not prop.startswith(k):
                continue

            ont_titles.append(str(v))

        ont_title: str | None = None
        if len(ont_titles) > 0:
            ont_title = str(ont_titles[0])

        return PropInfo(title=title, description=description, ont_title=ont_title)

    def __subject_object_dict(
        self, predicates: Sequence[URIRef], typ: type[T]
    ) -> dict[URIRef, list[T]]:
        """builds a dictionary { subject: list[objects] } with the given predicates"""

        so_dict: defaultdict[URIRef, list[T]] = defaultdict(list)

        for predicate in predicates:
            for sub, obj in self.g.subject_objects(predicate):
                if not isinstance(sub, URIRef):
                    continue
                if not isinstance(obj, typ):
                    continue
                so_dict[sub].append(obj)

        return dict(so_dict)
