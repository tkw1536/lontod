"""Dataclasses describing the meta ontology."""

from collections.abc import Generator
from contextlib import suppress
from dataclasses import dataclass
from typing import final, override

from rdflib.term import Literal, URIRef

from lontod.html import SPAN, A, NodeLike
from lontod.utils.frozendict import FrozenDict

from .core import HTMLable, RenderContext


@final
@dataclass(frozen=True)
class MetaOntologies:
    """Information about all meta ontologies."""

    types: FrozenDict[URIRef, tuple[URIRef, ...]]
    titles: FrozenDict[URIRef, tuple[Literal, ...]]
    props: FrozenDict[str, "MetaProperty"]

    def __getitem__(self, iri: URIRef) -> "MetaProperty":
        """Get information about a specific property."""
        return self.props[iri]

    def types_of(self, iri: URIRef) -> Generator[URIRef]:
        """Iterate over the types of the given IRI."""
        with suppress(KeyError):
            yield from self.types[iri]

    def title_of(self, iri: URIRef) -> Literal | None:
        """Return the title of the given IRI, if it exists in the metadata ontology."""
        try:
            return self.titles[iri][0]
        except KeyError:
            return None
        except IndexError:
            return None


@final
@dataclass(frozen=True)
class MetaOntology:
    """Information about a single ontology."""

    iri: URIRef
    titles: tuple[Literal, ...]

    def __contains__(self, iri: URIRef) -> bool:
        """Check if the given iri is contained in this ontology."""
        # TODO: Check where this is used and maybe go to something else instead.
        return iri.startswith(self.iri)


@final
@dataclass(frozen=True)
class MetaProperty(HTMLable):
    """Human-readable information about a specific property."""

    iri: URIRef
    """IRI of the property"""

    # title of the property
    titles: tuple[Literal, ...]
    """title of the property"""

    descriptions: tuple[Literal, ...]
    """description of the property"""

    ontologies: tuple[MetaOntology, ...]
    """ontologies this property is defined in."""

    @override
    def to_html(self, ctx: RenderContext | None = None) -> NodeLike:
        description_parts: list[str] = [
            str(description.value).rstrip(".") + "."
            for description in self.descriptions
        ]

        description_parts.extend(
            f"Defined in {', '.join(str(title) for title in ontology.titles)}."
            for ontology in self.ontologies
        )

        return A(
            (
                SPAN(
                    str(title.value).title(),
                    lang=title.language or False,
                )
                for title in self.titles
            ),
            title=" ".join(description_parts) if len(description_parts) > 0 else None,
            _class="hover_property",
            href=str(self.iri),
        )
