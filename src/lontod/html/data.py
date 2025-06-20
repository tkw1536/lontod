"""classes representing specific information about ontologies."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import override

from dominate.tags import a, html_tag, span
from rdflib.term import Literal, URIRef


class RenderContext:
    """context used for rendering."""

    def close(self) -> None:
        """Close this context, reserved for future usage."""

    def fragment(self, uri: URIRef) -> str:
        """Return a fragment identifier for this uri."""
        # TODO: keep track of state and use this once we've migrated rendering to appropriate functions!
        raise NotImplementedError


class HTMLable(ABC):
    """Represents an object that can be rendered as html."""

    @abstractmethod
    def to_html(self, ctx: RenderContext) -> html_tag:
        """Turn this class into html."""


@dataclass
class MetaOntology:
    """Information about a single ontology."""

    uri: URIRef
    titles: Sequence[Literal]

    def __contains__(self, uri: URIRef) -> bool:
        """Check if the given url is contained in this ontology."""
        return uri.startswith(self.uri)


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
