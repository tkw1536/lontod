"""information about rdf resources."""

# spellchecker:words uriref onts ASGS orcid xlink evenodd setclass inferencing

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import chain
from typing import Literal as TLiteral
from typing import override

import markdown
from dominate.tags import (
    a,
    br,
    html_tag,
    li,
    pre,
    span,
    sup,
    ul,
)
from dominate.util import container, raw, text
from rdflib.term import BNode, Literal, URIRef

from lontod.html.rdf_elements import (
    ONT_TYPES,
)
from lontod.utils.intersperse import intersperse

from .core import HTMLable, RenderContext

type _RDFResource = "BlankNodeResource|SetClassResource|_ResourceReference|RestrictionResource|LiteralResource|AgentResource"


@dataclass
class SetClassResource(HTMLable):
    """representation of a restriction."""

    cardinality: TLiteral["union", "intersection"] | None
    resources: Sequence[HTMLable]

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        joining_word: str
        if self.cardinality == "union":
            joining_word = "or"
        elif self.cardinality == "intersection":
            joining_word = "and"
        else:
            joining_word = ","

        return container(
            *intersperse(
                [resource.to_html(ctx) for resource in self.resources],
                span(joining_word, _class="_cardinality"),
            )
        )


@dataclass
class BlankNodeResource(HTMLable):
    """A BlankNode that isn't of a specific subtype."""

    node: BNode

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        return pre(str(self.node))


class _ResourceReference(HTMLable, ABC):
    """Reference to a resource by IRI."""

    iri: URIRef
    title: Literal

    @property
    @abstractmethod
    def is_local(self) -> bool:
        """Indicates if this resource is defined in the local ontology."""


@dataclass
class LocalResource(_ResourceReference):
    """Resource defined in the local ontology."""

    iri: URIRef
    title: Literal
    rdf_type: URIRef

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        fragment = ctx.fragment(self.iri)
        return span(
            a(str(self.title.value), href="#" + fragment),
            sup(
                ONT_TYPES[self.rdf_type][0],
                _class="sup-" + ONT_TYPES[self.rdf_type][0],
                title=ONT_TYPES[self.rdf_type][1],
            ),
        )

    @property
    @override
    def is_local(self) -> TLiteral[True]:
        """Indicates that this resource is defined within the local document."""
        return True


@dataclass
class ExternalResource(_ResourceReference):
    """Resource defined externally."""

    iri: URIRef
    title: Literal

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        return a(
            str(self.title.value),
            href=str(self.iri),
            target="_blank",
            rel="noreferrer noopener",
        )

    @property
    @override
    def is_local(self) -> TLiteral[False]:
        """Indicates that this resource is not defined within the local document."""
        return False


@dataclass
class RDFResources(HTMLable):
    """Information about a single RDF Resource."""

    resources: list[_RDFResource]

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        if len(self.resources) == 0:
            return container()
        if len(self.resources) == 1:
            return self.resources[0].to_html(ctx)
        u = ul()
        for resource in self.resources:
            u.appendChild(li(resource.to_html(ctx)))
        return u


@dataclass
class RestrictionResource(HTMLable):
    """OWL Restriction."""

    # list of properties this restriction is on
    properties: Sequence["_ResourceReference|AgentResource"]
    cardinalities: Sequence["_Cardinality"]

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        if len(self.properties) == 0 and len(self.cardinalities) == 0:
            return text("None")

        s = span()
        for elem in chain(
            (ref.to_html(ctx) for ref in self.properties),
            (card.to_html(ctx) for card in self.cardinalities),
        ):
            s.appendChild(elem)

        # TODO: not sure when we need this br!
        if len(self.properties) > 0 and len(self.cardinalities) > 0:
            s.appendChild(br())

        return s


@dataclass
class LiteralResource(HTMLable):
    """references a literal object node in the local different."""

    is_example: bool
    lit: Literal

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        if self.is_example:
            return pre(str(self.lit))

        # TODO: Language and smarter Content Type!
        return raw(markdown.markdown(self.lit))


@dataclass
class AgentResource(HTMLable):
    """represents an agent."""

    html: html_tag

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        return self.html


type _Cardinality = "CardinalityNumeric" | "CardinalityReference"


@dataclass
class CardinalityNumeric(HTMLable):
    """Numeric Cardinality."""

    typ: TLiteral["min", "max", "exactly"]
    value: str  # TODO: Should this be a literal?

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        return span(span(self.typ, _class="cardinality"), span(self.value))


@dataclass
class CardinalityReference(HTMLable):
    """Referencing Cardinality."""

    typ: TLiteral["only", "some", "value", "union", "intersection"]
    value: _ResourceReference

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        return span(
            span(self.typ, _class="cardinality"),
            span(
                self.value.to_html(ctx),
            ),
        )
