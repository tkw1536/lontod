"""rendering a single object."""

# spellchecker:words uriref onts ASGS orcid xlink evenodd setclass inferencing classset

from dataclasses import dataclass
from typing import Literal as TLiteral
from typing import final

from rdflib import Graph
from rdflib.namespace import (  # type: ignore[attr-defined]
    DCTERMS,
    OWL,
    PROV,
    RDF,
    SDO,
    SKOS,
    XSD,
    _is_valid_uri,
)
from rdflib.paths import ZeroOrMore
from rdflib.term import BNode, Literal, Node, URIRef

from lontod.ontologies.data.meta import MetaOntologies
from lontod.ontologies.data.rdf import (
    AGENT_PROPS,
    OWL_SET_TYPES,
    RESTRICTION_TYPES,
)
from lontod.ontologies.data.resource import (
    Affiliation,
    AgentResource,
    BlankNodeResource,
    CardinalityNumeric,
    CardinalityReference,
    LiteralResource,
    RDFResources,
    ResourceReference,
    RestrictionResource,
    SetClassResource,
    _Cardinality,
    _RDFResource,
)


@final
@dataclass(frozen=True)
class ResourceExtractor:
    """Extract information about a single resource from an ontology."""

    ont: Graph
    meta: MetaOntologies

    def __call__(self, *objects: Node, prop: URIRef | None) -> RDFResources:
        """Extract information about a given set of objects."""
        return RDFResources(
            resources=tuple(self.__extract(obj, prop) for obj in objects)
        )

    def __extract(
        self,
        obj: Node,
        prop: URIRef | None = None,
    ) -> _RDFResource:
        """Extract information about a single object."""
        if isinstance(obj, URIRef):
            return self.__extract_uri_ref(
                obj,
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

    def __extract_uri_ref(
        self,
        iri: URIRef,
    ) -> "ResourceReference|AgentResource":
        if (iri, RDF.type, PROV.Agent) in self.ont:
            return self.__extract_agent(iri)

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

        return ResourceReference(iri=iri, possible_title=title)

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
                self.__extract(o2)
                for o2 in self.ont.objects(o, RDF.rest * ZeroOrMore / RDF.first)  # type:ignore[operator]
            )
        return SetClassResource(cardinality=cardinality, resources=tuple(resources))

    def __extract_b_node_restriction(
        self,
        node: BNode,
    ) -> RestrictionResource:
        props: list[ResourceReference] = []
        cards: list[_Cardinality] = []

        for px, o in self.ont.predicate_objects(node):
            if px == RDF.type:
                continue

            if px == OWL.onProperty:
                if not isinstance(o, URIRef):
                    # TODO: warn if not?
                    continue
                on = self.__extract_uri_ref(o)
                if not isinstance(on, ResourceReference):
                    # TODO: warn if not?
                    continue
                props.append(on)
                continue

            if px in RESTRICTION_TYPES + OWL_SET_TYPES:
                card: _Cardinality | None = None
                if px in {
                    OWL.minCardinality,
                    OWL.minQualifiedCardinality,
                    OWL.maxCardinality,
                    OWL.maxQualifiedCardinality,
                    OWL.cardinality,
                    OWL.qualifiedCardinality,
                }:
                    card = self.__extract_cardinality_numeric(px, o)
                elif isinstance(o, URIRef):
                    card = self.__extract_cardinality_reference(px, o)

                if card is not None:
                    cards.append(card)

        return RestrictionResource(properties=tuple(props), cardinalities=tuple(cards))

    def __extract_cardinality_numeric(
        self, px: Node, o: Node
    ) -> CardinalityNumeric | None:
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
        return CardinalityNumeric(typ=typ, value=str(o))

    def __extract_cardinality_reference(
        self, px: Node, o: URIRef
    ) -> CardinalityReference | None:
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

        link = self.__extract_uri_ref(o)
        if not isinstance(link, ResourceReference):
            return None

        # TODO: Ensure that the type is actually an OWL.Class!
        return CardinalityReference(
            typ=card,
            value=link,
        )

    def __extract_literal(
        self,
        lit: Literal,
        prop: URIRef | None,
    ) -> "LiteralResource|ResourceReference|AgentResource":
        if self._is_valid_uri(str(lit)):
            uri = URIRef(str(lit))
            return self.__extract_uri_ref(uri)

        return LiteralResource(
            is_example=(prop == SKOS.example),
            lit=lit,
        )

    def _is_valid_uri(self, uri: str) -> bool:
        """Check if a URI is valid."""
        if not uri.startswith("http") and _is_valid_uri(uri):
            return False

        try:
            self.ont.namespace_manager.compute_qname(uri, False)
        except (ValueError, KeyError):
            return False

        return True

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
            names=tuple(names),
            prefixes=tuple(prefixes),
            identifiers=tuple(identifiers),
            urls=tuple(urls),
            emails=tuple(emails),
            affiliations=tuple(affiliations),
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
        return Affiliation(names=tuple(names), urls=tuple(urls))
