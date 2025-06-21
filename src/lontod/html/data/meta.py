"""Dataclasses describing the meta ontology."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import override

from dominate.tags import (
    a,
    span,
)
from rdflib.term import Literal, URIRef

from .core import HTMLable, RenderContext


@dataclass
class MetaOntology:
    """Information about a single ontology."""

    iri: URIRef
    titles: Sequence[Literal]

    def __contains__(self, iri: URIRef) -> bool:
        """Check if the given iri is contained in this ontology."""
        # TODO: Check where this is used and maybe go to something else insyead.
        return iri.startswith(self.iri)


@dataclass
class MetaProperty(HTMLable):
    """Human-readable information about a specific property."""

    # uri of this property
    uri: URIRef

    # title of the property
    titles: Sequence[Literal]

    # description of the property
    descriptions: Sequence[Literal]

    # ontologies this property is defined in
    ontologies: Sequence[MetaOntology]

    @override
    def to_html(self, ctx: RenderContext | None = None) -> a:
        description_parts: list[str] = [
            str(description.value).rstrip(".") + "."
            for description in self.descriptions
        ]

        description_parts.extend(
            f"Defined in {', '.join(str(title) for title in ontology.titles)}."
            for ontology in self.ontologies
        )

        titles = [
            span(
                str(title.value).title(),
                lang=title.language,
            )
            for title in self.titles
        ]

        return a(
            *titles,
            title=" ".join(description_parts) if len(description_parts) > 0 else None,
            _class="hover_property",
            href=str(self.uri),
        )
