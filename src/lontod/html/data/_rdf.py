"""various rdf namespaces."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import final

from rdflib import Namespace
from rdflib.namespace import (
    DCTERMS,
    OWL,
    RDF,
    RDFS,
    SDO,
    SKOS,
    VANN,
)
from rdflib.term import URIRef

# spellchecker:words RDFS VANN ONTDOC specialised

ONTDOC = Namespace("https://w3id.org/profile/ontdoc/")

# metadata properties for OWL Ontology instances
ONT_PROPS = (
    DCTERMS.title,
    DCTERMS.publisher,
    DCTERMS.creator,
    DCTERMS.contributor,
    DCTERMS.created,
    DCTERMS.dateAccepted,
    DCTERMS.modified,
    DCTERMS.issued,
    DCTERMS.license,
    DCTERMS.rights,
    SDO.category,
    OWL.versionIRI,
    OWL.versionInfo,
    OWL.priorVersion,
    SDO.identifier,
    VANN.preferredNamespacePrefix,
    VANN.preferredNamespaceUri,
    SKOS.historyNote,
    SKOS.scopeNote,
    DCTERMS.source,
    DCTERMS.provenance,
    SKOS.note,
    DCTERMS.description,
    ONTDOC.restriction,
)

# properties for OWL Class instances
CLASS_PROPS = (
    RDFS.isDefinedBy,
    DCTERMS.title,
    DCTERMS.description,
    SKOS.scopeNote,
    SKOS.example,
    DCTERMS.source,
    DCTERMS.provenance,
    SKOS.note,
    RDFS.subClassOf,
    OWL.equivalentClass,
    # OWL.restriction,
    ONTDOC.inDomainOf,
    ONTDOC.inDomainIncludesOf,
    ONTDOC.inRangeOf,
    ONTDOC.inRangeIncludesOf,
    ONTDOC.restriction,
    ONTDOC.hasInstance,
    ONTDOC.superClassOf,
)

# properties for instances of RDF Property and OWL specialised
# forms, such as ObjectProperty etc.
PROP_PROPS = (
    RDFS.isDefinedBy,
    DCTERMS.title,
    DCTERMS.description,
    SKOS.scopeNote,
    SKOS.example,
    DCTERMS.source,
    DCTERMS.provenance,
    SKOS.note,
    RDFS.subPropertyOf,
    ONTDOC.superPropertyOf,
    RDFS.domain,
    SDO.domainIncludes,
    RDFS.range,
    SDO.rangeIncludes,
)

# properties for Agents
AGENT_PROPS = (
    SDO.name,
    SDO.affiliation,
    SDO.identifier,
    SDO.email,
    SDO.honorificPrefix,
    SDO.url,
)

# properties for OWL restriction instances
RESTRICTION_PROPS = (
    OWL.allValuesFrom,
    OWL.someValuesFrom,
    OWL.hasValue,
    OWL.onProperty,
    OWL.onClass,
    OWL.cardinality,
    OWL.qualifiedCardinality,
    OWL.minCardinality,
    OWL.minQualifiedCardinality,
    OWL.maxCardinality,
    OWL.maxQualifiedCardinality,
)

# all known properties
PROPS = frozenset(
    ONT_PROPS + CLASS_PROPS + PROP_PROPS + AGENT_PROPS + RESTRICTION_PROPS,
)


@final
@dataclass
class PropertyKind:
    """Properties listed."""

    # TODO: rename to iri
    uri: URIRef

    @property
    def valid(self) -> bool:
        """Checks if this is a valid property kind."""
        return self.uri in ONT_TYPES

    @property
    def info(self) -> "_OntTypeInfo":
        """Information about this PropertyKind."""
        try:
            return ONT_TYPES[self.uri]
        except KeyError as err:
            raise InvalidPropertyKindError from err


class InvalidPropertyKindError(ValueError):
    """Raised when a PropertyKind is not valid."""


@final
@dataclass
class _OntTypeInfo:
    """Information about an ontology type."""

    abbrev: str
    toc_id: str

    inline_title: str
    plural_title: str
    properties: Sequence[URIRef]

    specializations: Sequence[URIRef]


ONT_TYPES = {
    OWL.Class: _OntTypeInfo(
        abbrev="c",
        toc_id="",
        inline_title="OWL/RDFS Class",
        plural_title="Classes",
        properties=CLASS_PROPS,
        specializations=(),
    ),
    RDF.Property: _OntTypeInfo(
        abbrev="p",
        toc_id="properties",
        inline_title="RDF Property",
        plural_title="Properties",
        properties=PROP_PROPS,
        specializations=(
            OWL.ObjectProperty,
            OWL.DatatypeProperty,
            OWL.AnnotationProperty,
            OWL.FunctionalProperty,
        ),
    ),
    OWL.ObjectProperty: _OntTypeInfo(
        abbrev="op",
        toc_id="objectproperties",
        inline_title="OWL Object Property",
        plural_title="Object Properties",
        properties=PROP_PROPS,
        specializations=(),
    ),
    OWL.DatatypeProperty: _OntTypeInfo(
        abbrev="dp",
        toc_id="datatypeproperties",
        inline_title="OWL Datatype Property",
        plural_title="Datatype Properties",
        properties=PROP_PROPS,
        specializations=(),
    ),
    OWL.AnnotationProperty: _OntTypeInfo(
        abbrev="ap",
        toc_id="annotationproperties",
        inline_title="OWL Annotation Property",
        plural_title="Annotation Properties",
        properties=PROP_PROPS,
        specializations=(),
    ),
    OWL.FunctionalProperty: _OntTypeInfo(
        abbrev="fp",
        toc_id="functionalproperties",
        inline_title="OWL Functional Property",
        plural_title="Functional Properties",
        properties=PROP_PROPS,
        specializations=(),
    ),
    # TODO: not sure about these!
    # OWL.InverseFunctionalProperty: _OntTypeInfo(
    #    abbrev="ifp",
    #    toc_id="",
    #    inline_title="OWL Inverse Functional Property",
    #    plural_title="",
    # ),
    # OWL.NamedIndividual: _OntTypeInfo(
    #    abbrev="ni",
    #    toc_id="named_individuals",
    #    inline_title="OWL Named Individual",
    #    plural_title="Named Individuals",
    # ),
}


RESTRICTION_TYPES = (
    OWL.cardinality,
    OWL.qualifiedCardinality,
    OWL.minCardinality,
    OWL.minQualifiedCardinality,
    OWL.maxCardinality,
    OWL.maxQualifiedCardinality,
    OWL.allValuesFrom,
    OWL.someValuesFrom,
    OWL.hasValue,
)

OWL_SET_TYPES = (OWL.unionOf, OWL.intersectionOf)
