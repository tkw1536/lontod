"""this file holds classes representing specific information about ontologies"""

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Sequence

from dominate.tags import a, html_tag, span  # type: ignore
from rdflib.term import Literal, URIRef


class RenderContext:
    """context used for rendering"""

    def close(self) -> None:
        """closes this context, reserved for future usage."""

    def fragment(self, uri: URIRef) -> str:
        """returns a fragment identifier for this uri"""

        # TODO: keep track of state and use this once we've migrated rendering to appropriate functions!
        raise NotImplementedError()


class HTMLable(metaclass=ABCMeta):
    """Represents an object that can be rendered as html"""

    @abstractmethod
    def to_html(self, ctx: RenderContext) -> html_tag:
        """turns this class into html"""


@dataclass
class MetaOntology:
    """Information about a single ontology"""

    uri: URIRef
    titles: Sequence[Literal]

    def __contains__(self, uri: URIRef) -> bool:
        """checks if the given url is contained in this ontology"""
        return uri.startswith(self.uri)


@dataclass
class MetaProperty(HTMLable):
    """Human-readable information about a specific property"""

    # uri of this property
    uri: URIRef

    # title of the property
    titles: Sequence[Literal]

    # description of the property
    descriptions: Sequence[Literal]

    # ontologies this property is defined in
    ontologies: Sequence[MetaOntology]

    def to_html(self, ctx: RenderContext | None = None) -> a:
        description_parts: list[str] = []
        for description in self.descriptions:
            description_parts.append(str(description.value).rstrip(".") + ".")

        for ontology in self.ontologies:
            description_parts.append(
                f"Defined in {", ".join(str(title) for title in ontology.titles)}.",
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
