"""information about rdf resources."""

# spellchecker:words uriref onts ASGS orcid xlink evenodd setclass inferencing noopener noreferer

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import chain
from typing import Final, final, override
from typing import Literal as TLiteral

from rdflib.term import BNode, Literal, URIRef

from lontod.html import (
    BR,
    CODE,
    DIV,
    EM,
    LI,
    PRE,
    SPAN,
    SUP,
    UL,
    A,
    NodeLike,
    RawNode,
)
from lontod.utils.intersperse import intersperse
from lontod.utils.partition import partition

from .core import HTMLable, RenderContext

type _RDFResource = "BlankNodeResource|SetClassResource|ResourceReference|RestrictionResource|LiteralResource|AgentResource"


@final
@dataclass(frozen=True)
class SetClassResource(HTMLable):
    """representation of a restriction."""

    cardinality: TLiteral["union", "intersection"] | None
    resources: Sequence[HTMLable]

    @override
    def to_html(self, ctx: RenderContext) -> NodeLike:
        joining_word: str
        if self.cardinality == "union":
            joining_word = "or"
        elif self.cardinality == "intersection":
            joining_word = "and"
        else:
            joining_word = ","

        return intersperse(
            [resource.to_html(ctx) for resource in self.resources],
            SPAN(joining_word, _class="_cardinality"),
        )


@final
@dataclass(frozen=True)
class BlankNodeResource(HTMLable):
    """A BlankNode that isn't of a specific subtype."""

    node: BNode

    @override
    def to_html(self, ctx: RenderContext) -> NodeLike:
        return PRE(str(self.node))


@final
@dataclass(frozen=True)
class ResourceReference(HTMLable):
    """Reference to a resource by IRI."""

    iri: URIRef
    possible_title: Literal

    @override
    def to_html(self, ctx: RenderContext) -> NodeLike:
        definiendum = ctx.ontology[self.iri]
        if definiendum is None:
            return A(
                str(self.possible_title.value),
                href=str(self.iri),
                target="_blank",
                rel="noreferrer noopener",
            )

        fragment = ctx.fragment(self.iri)
        return DIV(
            A(
                CODE(ctx.format_iri(definiendum.iri)),
                title=self.iri,
                href="#" + fragment,
            ),
            SUP(
                definiendum.prop.abbrev,
                _class="sup-" + definiendum.prop.abbrev,
                title=definiendum.prop.inline_title,
            ),
            _class="resource-ref",
        )


@final
@dataclass(frozen=True)
class RDFResources(HTMLable):
    """Information about a single RDF Resource."""

    resources: Sequence[_RDFResource]

    @override
    def to_html(self, ctx: RenderContext) -> NodeLike:
        if len(self.resources) == 0:
            return None
        if len(self.resources) == 1:
            return self.resources[0].to_html(ctx)

        return UL(LI(resource.to_html(ctx) for resource in self.resources))


@final
@dataclass(frozen=True)
class RestrictionResource(HTMLable):
    """OWL Restriction."""

    # list of properties this restriction is on
    properties: Sequence["ResourceReference|AgentResource"]
    cardinalities: Sequence["_Cardinality"]

    @override
    def to_html(self, ctx: RenderContext) -> NodeLike:
        if len(self.properties) == 0 and len(self.cardinalities) == 0:
            return "None"

        return SPAN(
            (ref.to_html(ctx) for ref in self.properties),
            (card.to_html(ctx) for card in self.cardinalities),
            # TODO: need to rework this
            # the layout looks bad
            BR(_class="todo")
            if len(self.properties) > 0 and len(self.cardinalities) > 0
            else None,
        )


@final
@dataclass(frozen=True)
class LiteralResource(HTMLable):
    """references a literal object node in the local different."""

    is_example: bool
    lit: Literal

    @override
    def to_html(self, ctx: RenderContext) -> NodeLike:
        if self.is_example:
            return PRE(str(self.lit))

        return ctx.render_content(self.lit)


@final
@dataclass(frozen=True)
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
    def to_html(self, ctx: RenderContext) -> NodeLike:
        # no names, just render the raw object!
        if len(self.names) == 0:
            return SPAN(str(self.obj))

        children: list[NodeLike] = []

        # build the names, grouped by language
        name_spans = (
            SPAN((str(lit.value) for lit in lits), lang=lang or False)
            for (lang, lits) in partition(
                chain(
                    self.prefixes,
                    self.names,
                ),
                lambda lit: lit.language,
            )
        )

        # build a name element
        name: NodeLike = intersperse(name_spans, BR())
        if len(self.urls) > 0:
            name = A(name, href=self.urls[0], target="_blank", rel="noopener noreferer")
        children.append(name)

        if "orcid.org" in self.obj:
            children.append(A(RawNode(_ORCID_LOGO), href=str(self.obj)))

        children.extend(
            A(
                RawNode(_ORCID_LOGO) if "orcid.org" in identifier else PRE(identifier),
                href=identifier,
            )
            for identifier in self.identifiers
        )

        emails: list[NodeLike] = []
        for email in self.emails:
            mail = email.replace("mailto:", "")
            emails.append(A(mail, href="mailto:" + mail))

        if len(emails) > 0:
            children.append("(")
            children.extend(intersperse(emails, ","))
            children.append(")")

        children.extend(af.to_html(ctx) for af in self.affiliations)

        return SPAN(children)


@final
@dataclass(frozen=True)
class Affiliation(HTMLable):
    """Affiliation of an agent."""

    names: Sequence[Literal]
    urls: Sequence[str]

    @override
    def to_html(self, ctx: RenderContext) -> NodeLike:
        # TODO: Multiple urls?
        the_url = self.urls[0] if len(self.urls) > 0 else None

        if len(self.names) > 0:
            return SPAN(
                EM(
                    " of ",
                    SPAN(
                        intersperse(
                            (
                                A(str(name.value), href=the_url)
                                if the_url is not None
                                else name
                                for name in names
                            ),
                            ",",
                        ),
                        lang=lang or False,
                    ),
                )
                for lang, names in partition(self.names, lambda x: x.language)
            )

        if the_url is not None:
            return SPAN(EM(" of ", A(the_url, href=the_url)))

        return SPAN()


type _Cardinality = "CardinalityNumeric" | "CardinalityReference"


@final
@dataclass(frozen=True)
class CardinalityNumeric(HTMLable):
    """Numeric Cardinality."""

    typ: TLiteral["min", "max", "exactly"]
    value: str  # TODO: Should this be a literal?

    @override
    def to_html(self, ctx: RenderContext) -> NodeLike:
        return SPAN(
            SPAN(self.typ, _class="cardinality"),
            SPAN(self.value),
        )


@final
@dataclass(frozen=True)
class CardinalityReference(HTMLable):
    """Referencing Cardinality."""

    typ: TLiteral["only", "some", "value", "union", "intersection"]
    value: ResourceReference

    @override
    def to_html(self, ctx: RenderContext) -> NodeLike:
        return SPAN(
            SPAN(self.typ, _class="cardinality"),
            SPAN(
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
