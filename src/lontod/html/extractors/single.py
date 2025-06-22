"""rendering a single object."""

# spellchecker:words uriref onts ASGS orcid xlink evenodd setclass inferencing

from dataclasses import dataclass
from typing import Literal as TLiteral

from rdflib import Graph
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, SDO, SKOS, XSD
from rdflib.paths import ZeroOrMore
from rdflib.term import BNode, Literal, Node, URIRef

from lontod.html.data.resource import (
    Affiliation,
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
from lontod.html.rdf_elements import (
    AGENT_PROPS,
    ONT_TYPES,
    OWL_SET_TYPES,
    RESTRICTION_TYPES,
)

from .meta import MetaExtractor


@dataclass
class SingleResourceExtractor:
    """Extract information about a single resource from an ontology."""

    ont: Graph
    meta: MetaExtractor

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

        # TODO: not sure I like this!
        names: list[Literal] = []
        prefixes: list[Literal] = []
        identifiers: list[str] = []
        urls: list[str] = []
        emails: list[str] = []
        affiliations: list[Affiliation] = []

        for px, o in self.ont.predicate_objects(obj):
            if px not in AGENT_PROPS:
                continue

            lit = o if isinstance(o, Literal) else None
            if lit is not None and isinstance(o, (Literal)):
                names.append(lit)
            elif px == SDO.honorificPrefix and isinstance(o, (Literal)):
                prefixes.append(o)
            elif px == SDO.identifier and isinstance(o, Literal | URIRef):
                identifiers.append(str(o))
            elif px == SDO.url:
                urls.append(str(o))
            elif px == SDO.email:
                emails.append(str(o))
            elif px == SDO.affiliation and isinstance(
                o,
                URIRef | BNode | Literal,
            ):
                affiliations.append(self._extract_affiliation(o))

        return AgentResource(
            obj=obj,
            names=names,
            prefixes=prefixes,
            identifiers=identifiers,
            urls=urls,
            emails=emails,
            affiliations=affiliations,
        )

    def _extract_affiliation(self, obj: URIRef | BNode | Literal) -> Affiliation:
        names: list[Literal] = []
        urls: list[str] = []
        for pa, o in self.ont.predicate_objects(obj):
            if pa not in AGENT_PROPS:
                continue

            if pa == SDO.name and isinstance(o, Literal):
                names.append(o)
            elif pa == SDO.URL:
                urls.append(str(o))
        return Affiliation(names=names, urls=urls)
