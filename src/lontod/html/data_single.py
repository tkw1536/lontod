"""rendering a single object."""

# spellchecker:words uriref onts ASGS orcid xlink evenodd setclass inferencing

from abc import ABC
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import chain
from typing import Literal as TLiteral
from typing import override

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
from rdflib import Graph
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, SDO, SKOS, XSD
from rdflib.paths import ZeroOrMore
from rdflib.term import BNode, Literal, Node, URIRef

from .common import intersperse
from .context import RenderContext
from .data import HTMLable
from .meta import MetaOntologies
from .rdf_elements import (
    AGENT_PROPS,
    ONT_TYPES,
    OWL_SET_TYPES,
    RESTRICTION_TYPES,
)


class RDFResource(HTMLable, ABC):
    """represents a single RDF resource."""


@dataclass
class BlankNodeObject(RDFResource):
    """a blank node."""


@dataclass
class SetClassResource(RDFResource):
    """representation of a restriction."""

    cardinality: TLiteral["union", "intersection"] | None
    resources: Sequence[RDFResource]

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
            intersperse(
                [resource.to_html(ctx) for resource in self.resources],
                span(joining_word, _class="_cardinality"),
            )
        )


@dataclass
class HyperlinkResource(RDFResource):
    """references a different node in the local document."""

    iri: URIRef  # what are we referring to?

    local: bool  # is the reference local to this ontology?
    title: Literal  # title of the object being referred to.
    rdf_type: URIRef | None  # type of the object being referred to, if known.

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        local_href = ctx.fragment(self.iri) if self.local else None
        (href, new_tab) = (
            ("#" + local_href, False)
            if local_href is not None
            else (str(self.iri), False)
        )

        rel, target = ("noreferrer noopener", "_blank") if new_tab else (None, None)

        link = a(str(self.title.value), href=href, target=target, rel=rel)

        if self.rdf_type is None:
            return link

        return span(
            link,
            sup(
                ONT_TYPES[self.rdf_type][0],
                _class="sup-" + ONT_TYPES[self.rdf_type][0],
                title=ONT_TYPES[self.rdf_type][1],
            ),
        )


@dataclass
class RDFResources(HTMLable):
    """Information about a single RDF Resource."""

    resources: list[RDFResource]

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


def rdf_obj_html(
    ctx: RenderContext,
    ont: Graph,
    meta: MetaOntologies,
    objs: Sequence[Node],
    rdf_type: URIRef | None = None,
    prop: URIRef | None = None,
) -> html_tag:
    """Create an object representation of a single resource."""
    # TODO: should these be grouped?
    return RDFResources(
        resources=[_single_resource(ont, meta, obj, rdf_type, prop) for obj in objs]
    ).to_html(ctx)


def _single_resource(
    ont: Graph,
    meta: MetaOntologies,
    obj: Node,
    rdf_type: URIRef | None,
    prop: URIRef | None = None,
) -> RDFResource:
    """Represent a single rdf object."""
    if isinstance(obj, URIRef):
        return _hyperlink_resource(
            ont,
            meta,
            obj,
            rdf_type=rdf_type,
        )
    if isinstance(obj, BNode):
        return _bn_resource(ont, meta, obj)
    if isinstance(obj, Literal):
        return _literal_resource(ont, meta, obj, prop)

    msg = f"unsupported resource type {obj!r}"
    raise TypeError(msg)


def _bn_resource(
    ont: Graph,
    meta: MetaOntologies,
    obj: BNode,
) -> RDFResource:
    if (obj, RDF.type, PROV.Agent) in ont:
        return _agent_resource(ont, obj)

    # TODO: remove back_onts and fids if not needed by subfunctions #pylint: disable=fixme
    # What kind of BN is it?
    # An Agent, a Restriction or a Set Class (union/intersection)
    # handled all typing added in OntDoc inferencing

    if (obj, RDF.type, OWL.Restriction) in ont:
        return _restriction_resource(ont, meta, obj)

    # set class: (obj, RDF.type, OWL.Class) in ont:
    return _setclass_resource(ont, obj, meta)


def _get_ont_type(ont: Graph, meta: MetaOntologies, iri: URIRef) -> URIRef | None:
    """Find the type of an object if it is known."""
    types_we_know = [
        OWL.Class,
        OWL.ObjectProperty,
        OWL.DatatypeProperty,
        OWL.AnnotationProperty,
        OWL.FunctionalProperty,
        RDF.Property,
    ]

    this_objects_types = [o for o in ont.objects(iri, RDF.type) if o in ONT_TYPES]

    for x_ in types_we_know:
        if x_ in this_objects_types:
            return x_

    this_objects_types.extend(o for o in meta.types_of(iri) if o in ONT_TYPES)

    for x_ in types_we_know:
        if x_ in this_objects_types:
            return x_

    return None


def _hyperlink_resource(
    ont: Graph,
    meta: MetaOntologies,
    iri: URIRef,
    rdf_type: URIRef | None = None,
) -> "HyperlinkResource|AgentResource":
    if (iri, RDF.type, PROV.Agent) in ont:
        return _agent_resource(ont, iri)

    # determine the type of the resource if we know it!
    rdf_type = _get_ont_type(ont, meta, iri) if rdf_type is None else rdf_type

    # consider ourselves as defined locally if we start with the Namespace.
    # TODO: should we check properly here?
    is_local = (iri, None, None) in ont

    # TODO: more than one title!

    # title from metadata?
    title: Literal | None = meta.title_of(iri)

    # title from ontology?
    if title is None:
        direct_title = ont.value(iri, DCTERMS.title)
        if isinstance(direct_title, Literal):
            title = direct_title

    # use the IRI itself as a title for the link
    if title is None:
        try:
            _, ns_uri, local = ont.compute_qname(iri, False)
            title = Literal(f"{ns_uri}{local}", datatype=XSD.anyURI)
        except KeyError:
            title = Literal(iri, datatype=XSD.anyURI)

    return HyperlinkResource(iri=iri, local=is_local, title=title, rdf_type=rdf_type)


def _setclass_resource(
    ont: Graph,
    obj: Node,
    meta: MetaOntologies,
) -> SetClassResource:
    """Union or intersection of different classes."""
    # TODO: This should properly render a tree: A union, or an intersection, or something else
    cardinality: TLiteral["union", "intersection"] | None = None
    if (obj, OWL.unionOf, None) in ont:
        cardinality = "union"
    elif (obj, OWL.intersectionOf, None) in ont:
        cardinality = "intersection"

    resources: list[RDFResource] = []
    for o in ont.objects(obj, OWL.unionOf | OWL.intersectionOf):
        resources.extend(
            _single_resource(
                ont,
                meta,
                o2,
                OWL.Class,
            )
            for o2 in ont.objects(o, RDF.rest * ZeroOrMore / RDF.first)  # type:ignore[operator]
        )
    return SetClassResource(cardinality=cardinality, resources=resources)


type _Cardinality = "CardinalityNumeric" | "CardinalityReference"


@dataclass
class RestrictionResource(RDFResource):
    """OWL Restriction."""

    # list of properties this restriction is on
    properties: Sequence["HyperlinkResource|AgentResource"]
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
    value: HyperlinkResource

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        return span(
            span(self.typ, _class="cardinality"),
            span(
                self.value.to_html(ctx),
            ),
        )


def _restriction_resource(
    ont: Graph,
    meta: MetaOntologies,
    obj: Node,
) -> RestrictionResource:
    props: list[HyperlinkResource] = []
    cards: list[_Cardinality] = []

    for px, o in ont.predicate_objects(obj):
        if px == RDF.type:
            continue

        if px == OWL.onProperty:
            if not isinstance(o, URIRef):
                # TODO: warn if not?
                continue
            on = _hyperlink_resource(ont, meta, o)
            if not isinstance(on, HyperlinkResource):
                # TODO: warn if not?
                continue
            props.append(on)
            continue

        if px in RESTRICTION_TYPES + OWL_SET_TYPES:
            if px in {
                OWL.minCardinality,
                OWL.minQualifiedCardinality,
                OWL.maxCardinality,
                OWL.maxQualifiedCardinality,
                OWL.cardinality,
                OWL.qualifiedCardinality,
            }:
                typ: TLiteral["min", "max", "exactly"]
                if px in {OWL.minCardinality, OWL.minQualifiedCardinality}:
                    typ = "min"
                elif px in {
                    OWL.maxCardinality,
                    OWL.maxQualifiedCardinality,
                }:
                    typ = "max"
                elif px in {OWL.cardinality, OWL.qualifiedCardinality}:
                    typ = "exactly"
                else:
                    msg = "never reached"
                    raise AssertionError(msg)

                # TODO: not sure about the literal here
                cards.append(
                    CardinalityNumeric(typ=typ, value=str(o)),
                )
            else:
                if not isinstance(o, URIRef):
                    continue

                card: TLiteral["only", "some", "value", "union", "intersection"]
                if px == OWL.allValuesFrom:
                    card = "only"
                elif px == OWL.someValuesFrom:
                    card = "some"
                elif px == OWL.hasValue:
                    card = "value"
                elif px == OWL.unionOf:
                    card = "union"
                elif px == OWL.intersectionOf:
                    card = "intersection"
                else:
                    msg = "never reached"
                    raise AssertionError(msg)

                link = _hyperlink_resource(
                    ont,
                    meta,
                    o,
                    OWL.Class,
                )
                if not isinstance(link, HyperlinkResource):
                    continue

                # TODO: Ensure that the type is actually an OWL.Class!
                cards.append(
                    CardinalityReference(
                        typ=card,
                        value=link,
                    ),
                )
    return RestrictionResource(properties=props, cardinalities=cards)


@dataclass
class LiteralResource(RDFResource):
    """references a literal object node in the local different."""

    is_example: bool
    content: Literal

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        if self.is_example:
            return pre(str(self.content))

        # TODO: Language and smarter Content Type!
        return raw(markdown.markdown(self.content))


def _literal_resource(
    ont: Graph,
    meta: MetaOntologies,
    obj: Literal,
    prop: URIRef | None,
) -> "LiteralResource|HyperlinkResource|AgentResource":
    # TODO: Properly check if it's a valid URI.
    if str(obj).startswith("http"):
        uri = URIRef(str(obj))
        return _hyperlink_resource(ont, meta, uri)

    return LiteralResource(
        is_example=(prop == SKOS.example),
        content=obj,
    )


@dataclass
class AgentResource(RDFResource):
    """represents an agent."""

    html: html_tag

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        return self.html


def _agent_resource(ont: Graph, obj: URIRef | BNode | Literal) -> AgentResource:
    def _affiliation_html(
        ont___: Graph,
        obj___: URIRef | BNode | Literal,
    ) -> html_tag:
        name_ = None
        url_ = None

        for p_, o_ in ont___.predicate_objects(obj___):
            if p_ in AGENT_PROPS:
                if p_ == SDO.name:
                    name_ = str(o_)
                elif p_ == SDO.url:
                    url_ = str(o_)

        sp_ = span()
        if name_ is not None:
            if url_ is not None:
                sp_.appendChild(em(" of ", a(name_, href=url_)))
            else:
                sp_.appendChild(em(" of ", name_))
        elif "http" in obj___:
            sp_.appendChild(em(" of ", a(obj___, href=obj___)))
        return sp_

    if isinstance(obj, Literal):
        return AgentResource(span(str(obj)))

    honorific_prefix = None
    name = None
    identifier = None
    orcid = None
    orcid_logo = """
            <svg width="15px" height="15px" viewBox="0 0 72 72" version="1.1"
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
    url = None
    email = None
    affiliation = None

    if "orcid.org" in str(obj):
        orcid = True

    for px, o in ont.predicate_objects(obj):
        if px in AGENT_PROPS:
            if px == SDO.name:
                name = str(o)
            elif px == SDO.honorificPrefix:
                honorific_prefix = str(o)
            elif px == SDO.identifier:
                identifier = str(o)
                if "orcid.org" in str(o):
                    orcid = True
            elif px == SDO.url:
                url = str(o)
            elif px == SDO.email:
                email = str(o)
            elif px == SDO.affiliation and isinstance(
                o,
                URIRef | BNode | Literal,
            ):
                affiliation = o

    sp = span()

    if name is not None:
        if honorific_prefix is not None:
            name = honorific_prefix + " " + name

        if url is not None:
            sp.appendChild(a(name, href=url))
        else:
            sp.appendChild(span(name))

        if orcid:
            if "orcid.org" in obj:
                sp.appendChild(a(raw(orcid_logo), href=obj))
            else:
                sp.appendChild(a(raw(orcid_logo), href=identifier))
        elif identifier is not None:
            sp.appendChild(a(identifier, href=identifier))
        if email is not None:
            email = email.replace("mailto:", "")
            sp.appendChild(span("(", a(email, href="mailto:" + email), " )"))

        if affiliation is not None:
            sp.appendChild(_affiliation_html(ont, affiliation))
    else:
        if not orcid:
            return AgentResource(obj)
        sp.appendChild(a(obj, href=obj))
    return AgentResource(sp)
