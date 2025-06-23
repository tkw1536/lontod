"""information about rdf resources."""

# spellchecker:words uriref onts ASGS orcid xlink evenodd setclass inferencing noopener noreferer

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import chain
from typing import Final, override
from typing import Literal as TLiteral

import markdown
from dominate.tags import (
    a,
    br,
    em,
    html_tag,
    li,
    pre,
    span,
    sup,
    ul,
)
from dominate.util import container, raw, text
from rdflib.term import BNode, Literal, URIRef

from lontod.utils.intersperse import intersperse
from lontod.utils.partition import partition

from ._rdf import PropertyKind
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
    rdf_type: PropertyKind

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        fragment = ctx.fragment(self.iri)
        info = self.rdf_type.info
        return span(
            a(str(self.title.value), href="#" + fragment),
            sup(
                info.abbrev,
                _class="sup-" + info.abbrev,
                title=info.inline_title,
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

    obj: URIRef | BNode
    names: Sequence[Literal]
    prefixes: Sequence[Literal]
    identifiers: Sequence[str]
    urls: Sequence[str]
    emails: Sequence[str]
    affiliations: Sequence["Affiliation"]

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        sp = span()

        # no names, just render the raw object!
        if len(self.names) == 0:
            return span(str(self.obj))

        # build the names, grouped by language
        name_spans: list[html_tag] = []
        for lang, lits in partition(
            chain(
                self.prefixes,
                self.names,
            ),
            lambda lit: lit.language,
        ):
            name_spans.extend(span(*(text(lit.value) for lit in lits), lang=lang))

        # build a name element
        name = container(*intersperse(name_spans, br()))
        if len(self.urls) > 0:
            name = a(name, href=self.urls[0], target="_blank", rel="noopener noreferer")
        sp.appendChild(name)

        if "orcid.org" in self.obj:
            sp.appendChild(a(raw(_ORCID_LOGO), href=str(self.obj)))

        for identifier in self.identifiers:
            sp.appendChild(
                a(
                    raw(_ORCID_LOGO) if "orcid.org" in identifier else pre(identifier),
                    href=identifier,
                )
            )

        emails = []
        for email in self.emails:
            mail = email.replace("mailto:", "")
            emails.append(a(mail, href="mailto:" + mail))

        # add the
        if len(emails) > 0:
            sp.appendChild("(")
            for child in intersperse(emails, text(",")):
                sp.appendChild(child)
            sp.appendChild(")")

        for af in self.affiliations:
            sp.appendChild(af.to_html(ctx))

        return sp


@dataclass
class Affiliation(HTMLable):
    """Affiliation of an agent."""

    names: Sequence[Literal]
    urls: Sequence[str]

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        sp = span()

        # TODO: Multiple urls
        the_url = self.urls[0] if len(self.urls) > 0 else None

        if len(self.names) > 0:
            for lang, names in partition(self.names, lambda x: x.language):
                sp.appendChild(
                    em(
                        " of ",
                        span(
                            *intersperse(
                                (
                                    a(str(name.value), href=the_url)
                                    if the_url is not None
                                    else name
                                    for name in names
                                ),
                                text(","),
                            ),
                            lang=lang,
                        ),
                    )
                )

        elif the_url is not None:
            sp.appendChild(em(" of ", a(the_url, href=the_url)))

        return sp


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


_ORCID_LOGO: Final = """<svg width="15px" height="15px" viewBox="0 0 72 72" version="1.1"
xmlns="http://www.w3.org/2000/svg"
xmlns:xlink="http://www.w3.org/1999/xlink">
<title>Orcid logo</title>
<g id="Symbols" stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
    <g id="hero" transform="translate(-924.000000, -72.000000)" fill-rule="nonzero">
        <g id="Group-4">
            <g id="vector_iD_icon" transform="translate(924.000000, 72.000000)">
                <path d="M72,36 C72,55.884375 55.884375,72 36,72 C16.115625,72 0,55.884375 0,36 C0,16.115625 16.115625,0 36,0 C55.884375,0 72,16.115625 72,36 Z" id="Path" fill="#A6CE39"></path>
                <g id="Group" transform="translate(18.868966, 12.910345)" fill="#FFFFFF">
                    <polygon id="Path" points="5.03734929 39.1250878 0.695429861 39.1250878 0.695429861 9.14431787 5.03734929 9.14431787 5.03734929 22.6930505 5.03734929 39.1250878"></polygon>
                    <path d="M11.409257,9.14431787 L23.1380784,9.14431787 C34.303014,9.14431787 39.2088191,17.0664074 39.2088191,24.1486995 C39.2088191,31.846843 33.1470485,39.1530811 23.1944669,39.1530811 L11.409257,39.1530811 L11.409257,9.14431787 Z M15.7511765,35.2620194 L22.6587756,35.2620194 C32.49858,35.2620194 34.7541226,27.8438084 34.7541226,24.1486995 C34.7541226,18.1301509 30.8915059,13.0353795 22.4332213,13.0353795 L15.7511765,13.0353795 L15.7511765,35.2620194 Z" id="Shape"></path>
                    <path d="M5.71401206,2.90182329 C5.71401206,4.441452 4.44526937,5.72914146 2.86638958,5.72914146 C1.28750978,5.72914146 0.0187670918,4.441452 0.0187670918,2.90182329 C0.0187670918,1.33420133 1.28750978,0.0745051096 2.86638958,0.0745051096 C4.44526937,0.0745051096 5.71401206,1.36219458 5.71401206,2.90182329 Z" id="Path"></path>
                </g>
            </g>
        </g>
    </g>
</g>
</svg>"""
