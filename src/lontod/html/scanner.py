"""parses an ontology as html."""

from collections import defaultdict
from collections.abc import Generator, Sequence
from itertools import chain
from typing import cast

from rdflib import Graph, Literal
from rdflib.namespace import (
    DC,
    DCTERMS,
    FOAF,
    ORG,
    OWL,
    PROF,
    PROV,
    RDF,
    RDFS,
    SDO,
    SKOS,
)
from rdflib.term import Node, URIRef

from .data._rdf import (
    AGENT_PROPS,
    ONT_PROPS,
    ONTDOC,
    PropertyKind,
)
from .data.core import RenderContext
from .data.ontology import (
    Ontology,
    OntologyDefinienda,
    PropertyResourcePair,
    TypeDefinienda,
)
from .extractors.meta import MetaExtractor
from .extractors.ontology import OntologyExtractor
from .extractors.resource import ResourceExtractor
from .utils import (
    sort_ontology,
)

# spellchecker:words ONTDOC FOAF RDFS onts Helper objectproperties datatypeproperties annotationproperties functionalproperties nses


class Scanner:
    """Scans an ontology."""

    def __init__(self, ontology: Graph) -> None:
        """Create a new Ontology."""
        self.__ont = sort_ontology(ontology)
        self._ontdoc_inference(self.__ont)

        self.__meta = MetaExtractor()()
        self.__res = ResourceExtractor(self.__ont, self.__meta)
        self.__extractor = OntologyExtractor(
            ont=self.__ont,
            meta=self.__meta,
            res=self.__res,
        )

    def _ontdoc_inference(self, g: Graph) -> None:
        """Expand the ontology's graph to make OntDoc querying easier.

        Uses axioms made up for OntDoc, but they are simple and obvious
        and don't collide with well-known ontologies
        """
        # class types
        for s_ in g.subjects(RDF.type, RDFS.Class):
            g.add((s_, RDF.type, OWL.Class))

        # # property types
        # for s_ in chain(
        #     g.subjects(RDF.type, OWL.ObjectProperty),
        #     g.subjects(RDF.type, OWL.FunctionalProperty),
        #     g.subjects(RDF.type, OWL.DatatypeProperty),
        #     g.subjects(RDF.type, OWL.AnnotationProperty),
        # ):
        #     g.add((s_, RDF.type, RDF.Property))

        # name
        for s_, o in chain(
            g.subject_objects(DC.title),
            g.subject_objects(RDFS.label),
            g.subject_objects(SKOS.prefLabel),
            g.subject_objects(SDO.name),
        ):
            g.add((s_, DCTERMS.title, o))

        # description
        for s_, o in chain(
            g.subject_objects(DC.description),
            g.subject_objects(RDFS.comment),
            g.subject_objects(SKOS.definition),
            g.subject_objects(SDO.description),
        ):
            g.add((s_, DCTERMS.description, o))

        # source
        for s_, o in g.subject_objects(DC.source):
            g.add((s_, DCTERMS.source, o))

        # license
        for s_, o in g.subject_objects(SDO.license):
            g.add((s_, DCTERMS.license, o))

        #
        #   Blank Node Types
        #
        for s_ in g.subjects(OWL.onProperty, None):
            g.add((s_, RDF.type, OWL.Restriction))

        for s_ in chain(
            g.subjects(OWL.unionOf, None),
            g.subjects(OWL.intersectionOf, None),
        ):
            g.add((s_, RDF.type, OWL.Class))

        # we do these next few so we only need to loop through
        # Class & Property properties once: single subject
        for s_, o in g.subject_objects(RDFS.subClassOf):
            g.add((o, ONTDOC.superClassOf, s_))

        for s_, o in g.subject_objects(RDFS.subPropertyOf):
            g.add((o, ONTDOC.superPropertyOf, s_))

        for s_, o in g.subject_objects(RDFS.domain):
            g.add((o, ONTDOC.inDomainOf, s_))

        for s_, o in g.subject_objects(SDO.domainIncludes):
            g.add((o, ONTDOC.inDomainIncludesOf, s_))

        for s_, o in g.subject_objects(RDFS.range):
            g.add((o, ONTDOC.inRangeOf, s_))

        for s_, o in g.subject_objects(SDO.rangeIncludes):
            g.add((o, ONTDOC.inRangeIncludesOf, s_))

        for s_, o in g.subject_objects(RDF.type):
            g.add((o, ONTDOC.hasMember, s_))

        #
        #   Agents
        #
        # creator
        for s_, o in chain(
            g.subject_objects(DC.creator),
            g.subject_objects(SDO.creator),
            g.subject_objects(SDO.author),
        ):
            g.remove((s_, DC.creator, o))
            g.remove((s_, SDO.creator, o))
            g.remove((s_, SDO.author, o))
            g.add((s_, DCTERMS.creator, o))

        # contributor
        for s_, o in chain(
            g.subject_objects(DC.contributor),
            g.subject_objects(SDO.contributor),
        ):
            g.remove((s_, DC.contributor, o))
            g.remove((s_, SDO.contributor, o))
            g.add((s_, DCTERMS.contributor, o))

        # publisher
        for s_, o in chain(
            g.subject_objects(DC.publisher),
            g.subject_objects(SDO.publisher),
        ):
            g.remove((s_, DC.publisher, o))
            g.remove((s_, SDO.publisher, o))
            g.add((s_, DCTERMS.publisher, o))

        # indicate Agent instances from properties
        for o in chain(
            g.objects(None, DCTERMS.publisher),
            g.objects(None, DCTERMS.creator),
            g.objects(None, DCTERMS.contributor),
        ):
            g.add((o, RDF.type, PROV.Agent))

        # Agent annotations
        for s_, o in g.subject_objects(FOAF.name):
            g.add((s_, SDO.name, o))

        for s_, o in g.subject_objects(FOAF.mbox):
            g.add((s_, SDO.email, o))

        for s_, o in g.subject_objects(ORG.memberOf):
            g.add((s_, SDO.affiliation, o))

    def render(self) -> str:
        """Render this document into a string."""
        ont = self._render()
        html = ont.to_html(RenderContext())
        return cast("str", html.render(pretty=True))

    def _make_metadata(self) -> OntologyDefinienda:
        this_onts_props: dict[URIRef, list[Node]] = defaultdict(list)
        # get all ONT_PROPS props and their (multiple) values
        for s_ in chain(
            self.__ont.subjects(predicate=RDF.type, object=OWL.Ontology),
            self.__ont.subjects(predicate=RDF.type, object=SKOS.ConceptScheme),
            self.__ont.subjects(predicate=RDF.type, object=PROF.Profile),
        ):
            if not isinstance(s_, URIRef):
                continue
            iri = s_
            for p_, o in self.__ont.predicate_objects(s_):
                if p_ not in ONT_PROPS:
                    continue
                if not isinstance(p_, URIRef):
                    # always True because ONT_PROPS only has URIRefs
                    msg = "never reached"
                    raise TypeError(msg)
                this_onts_props[p_].append(o)

        our_props: list[PropertyResourcePair] = []
        for prop_iri in ONT_PROPS:
            if prop_iri not in this_onts_props:
                continue
            our_props.append(
                PropertyResourcePair(
                    prop=self.__meta[prop_iri],
                    resources=self.__res(
                        *this_onts_props[prop_iri], rdf_type=None, prop=prop_iri
                    ),
                )
            )

        return OntologyDefinienda(
            iri=iri,
            titles=[
                x for x in this_onts_props[DCTERMS.title] if isinstance(x, Literal)
            ],
            properties=our_props,
        )

    @property
    def schema(self) -> Graph:
        """Generic schema.org description for this graph."""
        sdo = Graph()
        for ont_iri in chain(
            self.__ont.subjects(predicate=RDF.type, object=OWL.Ontology),
            self.__ont.subjects(predicate=RDF.type, object=SKOS.ConceptScheme),
            self.__ont.subjects(predicate=RDF.type, object=PROF.Profile),
        ):
            sdo.add((ont_iri, RDF.type, SDO.DefinedTermSet))

            for p_, o in self.__ont.predicate_objects(ont_iri):
                if p_ == DCTERMS.title:
                    sdo.add((ont_iri, SDO.name, o))
                elif p_ == DCTERMS.description:
                    sdo.add((ont_iri, SDO.description, o))
                elif p_ == DCTERMS.publisher:
                    sdo.add((ont_iri, SDO.publisher, o))
                    if isinstance(o, Literal):
                        continue
                    for p2, o2 in self.__ont.predicate_objects(o):
                        if p2 in AGENT_PROPS:
                            sdo.add((o, p2, o2))
                elif p_ == DCTERMS.creator:
                    sdo.add((ont_iri, SDO.creator, o))
                    if isinstance(o, Literal):
                        continue
                    for p2, o2 in self.__ont.predicate_objects(o):
                        if p2 in AGENT_PROPS:
                            sdo.add((o, p2, o2))
                elif p_ == DCTERMS.contributor:
                    sdo.add((ont_iri, SDO.contributor, o))
                    if isinstance(o, Literal):
                        continue
                    for p2, o2 in self.__ont.predicate_objects(o):
                        if p2 in AGENT_PROPS:
                            sdo.add((o, p2, o2))
                elif p_ == DCTERMS.created:
                    sdo.add((ont_iri, SDO.dateCreated, o))
                elif p_ == DCTERMS.modified:
                    sdo.add((ont_iri, SDO.dateModified, o))
                elif p_ == DCTERMS.issued:
                    sdo.add((ont_iri, SDO.dateIssued, o))
                elif p_ == DCTERMS.license:
                    sdo.add((ont_iri, SDO.license, o))
                elif p_ == DCTERMS.rights:
                    sdo.add((ont_iri, SDO.copyrightNotice, o))

        return sdo

    def _render(self) -> Ontology:
        return Ontology(
            schema_json=self.schema.serialize(format="json-ld"),
            metadata=self._make_metadata(),
            sections=tuple(self.__make_sections()),
            namespaces=self.__make_namespaces(),
        )

    def __make_sections(self) -> Generator[TypeDefinienda]:
        for kind_iri in (
            OWL.Class,
            RDF.Property,
            OWL.ObjectProperty,
            OWL.DatatypeProperty,
            OWL.AnnotationProperty,
            OWL.FunctionalProperty,
        ):
            if (None, RDF.type, kind_iri) not in self.__ont:
                continue

            yield self.__extractor.extract(PropertyKind(kind_iri))

    def __make_namespaces(self) -> Sequence[tuple[str, URIRef]]:
        # only get namespaces used in ont
        nses: dict[str, URIRef] = {}
        for n in chain(
            self.__ont.subjects(), self.__ont.predicates(), self.__ont.objects()
        ):
            # a list of prefixes we don't like
            excluded_namespaces = (
                # "https://linked.data.gov.au/def/"
            )
            if str(n).startswith(excluded_namespaces):
                continue
            nses.update(
                {
                    prefix: ns
                    for (prefix, ns) in self.__ont.namespaces()
                    if str(n).startswith(ns)
                }
            )

        return tuple(sorted(nses.items(), key=lambda x: x[0]))
