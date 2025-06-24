"""various rdf namespaces."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import final

from rdflib.namespace import (
    DCTERMS,
    OWL,
    RDF,
    RDFS,
    SDO,
    SKOS,
    VANN,
    DefinedNamespace,
    Namespace,
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


class InvalidPropertyKindError(ValueError):
    """Raised when a PropertyKind is not valid."""


@dataclass(frozen=True)
class _IndexedProperty:
    """Information about an ontology type."""

    iri: URIRef

    inline_title: str
    plural_title: str

    abbrev: str

    specializations: Sequence[URIRef]
    properties: Sequence[URIRef]


@final
class IndexedProperty(_IndexedProperty, Enum):
    """Classification of properties."""

    CLASS = (OWL.Class, "OWL/RDFS Class", "Classes", "c", (), CLASS_PROPS)
    PROPERTY = (
        RDF.Property,
        "RDF Property",
        "Properties",
        "p",
        (
            OWL.ObjectProperty,
            OWL.DatatypeProperty,
            OWL.AnnotationProperty,
            OWL.FunctionalProperty,
            OWL.InverseFunctionalProperty,
        ),
        PROP_PROPS,
    )
    OBJECT_PROPERTY = (
        OWL.ObjectProperty,
        "OWL Object Property",
        "Object Properties",
        "op",
        PROP_PROPS,
        (),
    )
    DATATYPE_PROPERTY = (
        OWL.DatatypeProperty,
        "OWL Datatype Property",
        "Datatype Properties",
        "dp",
        PROP_PROPS,
        (),
    )
    ANNOTATION_PROPERTY = (
        OWL.AnnotationProperty,
        "OWL Annotation Property",
        "Annotation Properties",
        "ap",
        PROP_PROPS,
        (),
    )
    FUNCTIONAL_PROPERTY = (
        OWL.FunctionalProperty,
        "OWL Functional Property",
        "Functional Properties",
        "fp",
        PROP_PROPS,
        (),
    )
    INVERSE_FUNCTIONAL_PROPERTY = (
        OWL.InverseFunctionalProperty,
        "OWL Inverse Functional Property",
        "Inverse Functional Properties",
        "ifp",
        (),
        PROP_PROPS,
    )
    NAMED_INDIVIDUAL = (
        OWL.NamedIndividual,
        "OWL Named Individual",
        "Named Individuals",
        "ni",
        (),
        PROP_PROPS,
    )


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


class LONTOD(DefinedNamespace):
    """Special namespace used only internally by lontod."""

    Metadata: URIRef
    Namespaces: URIRef
    Legend: URIRef

    _NS = Namespace("https://github.com/tkw1536/lontod#")
