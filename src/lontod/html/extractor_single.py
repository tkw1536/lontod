"""rendering a single object."""

# spellchecker:words uriref onts ASGS orcid xlink evenodd setclass inferencing

from dataclasses import dataclass
from typing import Literal as TLiteral

from dominate.tags import (
    a,
    em,
    html_tag,
    span,
)
from dominate.util import raw
from rdflib import Graph
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, SDO, SKOS, XSD
from rdflib.paths import ZeroOrMore
from rdflib.term import BNode, Literal, Node, URIRef

from .data.resource import (
    AgentResource,
    BlankNodeResource,
    CardinalityNumeric,
    CardinalityReference,
    ExternalResource,
    LiteralResource,
    LocalResource,
    RDFResources,
    RestrictionResource,
    SetClassResource,
    _Cardinality,
    _RDFResource,
    _ResourceReference,
)
from .extractor_meta import MetaOntologies
from .rdf_elements import (
    AGENT_PROPS,
    ONT_TYPES,
    OWL_SET_TYPES,
    RESTRICTION_TYPES,
)


@dataclass
class SingleResourceExtractor:
    """Extract information about a single resource from an ontology."""

    ont: Graph
    meta: MetaOntologies

    def __call__(
        self, *objects: Node, rdf_type: URIRef | None, prop: URIRef | None
    ) -> RDFResources:
        """Extract information about a given set of objects."""
        return RDFResources(
            resources=[self.__extract(obj, rdf_type, prop) for obj in objects]
        )

    def __extract(
        self,
        obj: Node,
        rdf_type: URIRef | None,
        prop: URIRef | None = None,
    ) -> _RDFResource:
        """Extract information about a single object."""
        if isinstance(obj, URIRef):
            return self.__extract_uri_ref(
                obj,
                rdf_type=rdf_type,
            )
        if isinstance(obj, BNode):
            return self.__extract_b_node(obj)
        if isinstance(obj, Literal):
            return self.__extract_literal(obj, prop)

        msg = f"unsupported resource type {obj!r}"
        raise TypeError(msg)

    def __extract_b_node(
        self,
        node: BNode,
    ) -> _RDFResource:
        if (node, RDF.type, PROV.Agent) in self.ont:
            return self.__extract_agent(node)

        if (node, RDF.type, OWL.Restriction) in self.ont:
            return self.__extract_b_node_restriction(node)

        if (node, RDF.type, OWL.Class) in self.ont:
            return self.__extract_b_node_classset(node)

        return BlankNodeResource(node=node)

    def _get_ont_type(self, iri: URIRef) -> URIRef | None:
        """Find the type of an object if it is known."""
        # TODO: Use this as an enum or something
        types_we_know = [
            OWL.Class,
            OWL.ObjectProperty,
            OWL.DatatypeProperty,
            OWL.AnnotationProperty,
            OWL.FunctionalProperty,
            RDF.Property,
        ]

        this_objects_types = [
            o for o in self.ont.objects(iri, RDF.type) if o in ONT_TYPES
        ]

        for x_ in types_we_know:
            if x_ in this_objects_types:
                return x_

        this_objects_types.extend(o for o in self.meta.types_of(iri) if o in ONT_TYPES)

        for x_ in types_we_know:
            if x_ in this_objects_types:
                return x_

        return None

    def __extract_uri_ref(
        self,
        iri: URIRef,
        rdf_type: URIRef | None = None,
    ) -> "_ResourceReference|AgentResource":
        if (iri, RDF.type, PROV.Agent) in self.ont:
            return self.__extract_agent(iri)

        # determine the type of the resource if we know it!
        rdf_type = self._get_ont_type(iri) if rdf_type is None else rdf_type

        # consider something as defined if it exists within the current ontology.
        # TODO: not sure if we should to more extensive checks here, like having a given type.
        is_local = (iri, None, None) in self.ont

        # TODO: more than one title!

        # title from metadata?
        title: Literal | None = self.meta.title_of(iri)

        # title from ontology?
        if title is None:
            direct_title = self.ont.value(iri, DCTERMS.title)
            if isinstance(direct_title, Literal):
                title = direct_title

        # use the IRI itself as a title for the link
        if title is None:
            try:
                _, ns_uri, local = self.ont.compute_qname(iri, False)
                title = Literal(f"{ns_uri}{local}", datatype=XSD.anyURI)
            except KeyError:
                title = Literal(iri, datatype=XSD.anyURI)

        if is_local and rdf_type is not None:
            return LocalResource(iri=iri, title=title, rdf_type=rdf_type)
        return ExternalResource(iri=iri, title=title)

    def __extract_b_node_classset(
        self,
        node: BNode,
    ) -> SetClassResource:
        """Union or intersection of different classes."""
        # TODO: This should properly render a tree: A union, or an intersection, or something else
        cardinality: TLiteral["union", "intersection"] | None = None
        if (node, OWL.unionOf, None) in self.ont:
            cardinality = "union"
        elif (node, OWL.intersectionOf, None) in self.ont:
            cardinality = "intersection"

        resources: list[_RDFResource] = []
        for o in self.ont.objects(node, OWL.unionOf | OWL.intersectionOf):
            resources.extend(
                self.__extract(
                    o2,
                    OWL.Class,
                )
                for o2 in self.ont.objects(o, RDF.rest * ZeroOrMore / RDF.first)  # type:ignore[operator]
            )
        return SetClassResource(cardinality=cardinality, resources=resources)

    def __extract_b_node_restriction(
        self,
        node: BNode,
    ) -> RestrictionResource:
        props: list[_ResourceReference] = []
        cards: list[_Cardinality] = []

        for px, o in self.ont.predicate_objects(node):
            if px == RDF.type:
                continue

            if px == OWL.onProperty:
                if not isinstance(o, URIRef):
                    # TODO: warn if not?
                    continue
                on = self.__extract_uri_ref(o)
                if not isinstance(on, _ResourceReference):
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

                    link = self.__extract_uri_ref(o, OWL.Class)
                    if not isinstance(link, _ResourceReference):
                        continue

                    # TODO: Ensure that the type is actually an OWL.Class!
                    cards.append(
                        CardinalityReference(
                            typ=card,
                            value=link,
                        ),
                    )
        return RestrictionResource(properties=props, cardinalities=cards)

    def __extract_literal(
        self,
        lit: Literal,
        prop: URIRef | None,
    ) -> "LiteralResource|_ResourceReference|AgentResource":
        # TODO: Properly check if it's a valid URI.
        if str(lit).startswith("http"):
            uri = URIRef(str(lit))
            return self.__extract_uri_ref(uri)

        return LiteralResource(
            is_example=(prop == SKOS.example),
            lit=lit,
        )

    def __extract_agent(self, obj: URIRef | BNode) -> AgentResource:
        # TODO: Rework this
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

        for px, o in self.ont.predicate_objects(obj):
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
                sp.appendChild(_affiliation_html(self.ont, affiliation))
        else:
            if not orcid:
                return AgentResource(obj)
            sp.appendChild(a(obj, href=obj))
        return AgentResource(sp)
