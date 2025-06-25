"""extracting information about an ontology as a whole."""

from collections import defaultdict
from collections.abc import Generator, Sequence
from functools import cached_property
from itertools import chain

from rdflib import Graph, Literal, Node, URIRef
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
    XSD,
)

from lontod.ontologies.data.ontology import (
    Definiendum,
    Ontology,
    OntologyDefinienda,
    PropertyResourcePair,
    TypeDefinienda,
)
from lontod.ontologies.data.rdf import AGENT_PROPS, ONT_PROPS, ONTDOC, IndexedProperty
from lontod.ontologies.extractors.core import iri_to_title
from lontod.ontologies.extractors.resource import ResourceExtractor
from lontod.utils.graph import sort, used_namespaces

from .meta import MetaExtractor


class OntologyExtractor:
    """Extracts information about a single ontology."""

    def __init__(self, ontology: Graph) -> None:
        """Create a new Ontology."""
        self.__ont = sort(ontology)
        OntologyExtractor.__ontdoc_inference(self.__ont)

        self.__meta = MetaExtractor()()
        self.__res = ResourceExtractor(self.__ont, self.__meta)

    @staticmethod
    def __ontdoc_inference(graph: Graph) -> None:  # noqa: PLR0912 C901
        """Expand the ontology's graph to make OntDoc querying easier.

        Uses axioms made up for OntDoc, but they are simple and obvious
        and don't collide with well-known ontologies
        """
        # class types
        for s_ in graph.subjects(RDF.type, RDFS.Class):
            graph.add((s_, RDF.type, OWL.Class))
        # name
        for s_, o in chain(
            graph.subject_objects(DC.title),
            graph.subject_objects(RDFS.label),
            graph.subject_objects(SKOS.prefLabel),
            graph.subject_objects(SDO.name),
        ):
            graph.add((s_, DCTERMS.title, o))

        # description
        for s_, o in chain(
            graph.subject_objects(DC.description),
            graph.subject_objects(RDFS.comment),
            graph.subject_objects(SKOS.definition),
            graph.subject_objects(SDO.description),
        ):
            graph.add((s_, DCTERMS.description, o))

        # source
        for s_, o in graph.subject_objects(DC.source):
            graph.add((s_, DCTERMS.source, o))

        # license
        for s_, o in graph.subject_objects(SDO.license):
            graph.add((s_, DCTERMS.license, o))

        #
        #   Blank Node Types
        #
        for s_ in graph.subjects(OWL.onProperty, None):
            graph.add((s_, RDF.type, OWL.Restriction))

        for s_ in chain(
            graph.subjects(OWL.unionOf, None),
            graph.subjects(OWL.intersectionOf, None),
        ):
            graph.add((s_, RDF.type, OWL.Class))

        # we do these next few so we only need to loop through
        # Class & Property properties once: single subject
        for s_, o in graph.subject_objects(RDFS.subClassOf):
            graph.add((o, ONTDOC.superClassOf, s_))

        for s_, o in graph.subject_objects(RDFS.subPropertyOf):
            graph.add((o, ONTDOC.superPropertyOf, s_))

        for s_, o in graph.subject_objects(RDFS.domain):
            graph.add((o, ONTDOC.inDomainOf, s_))

        for s_, o in graph.subject_objects(SDO.domainIncludes):
            graph.add((o, ONTDOC.inDomainIncludesOf, s_))

        for s_, o in graph.subject_objects(RDFS.range):
            graph.add((o, ONTDOC.inRangeOf, s_))

        for s_, o in graph.subject_objects(SDO.rangeIncludes):
            graph.add((o, ONTDOC.inRangeIncludesOf, s_))

        for s_, o in graph.subject_objects(RDF.type):
            graph.add((o, ONTDOC.hasMember, s_))

        #
        #   Agents
        #
        # creator
        for s_, o in chain(
            graph.subject_objects(DC.creator),
            graph.subject_objects(SDO.creator),
            graph.subject_objects(SDO.author),
        ):
            graph.remove((s_, DC.creator, o))
            graph.remove((s_, SDO.creator, o))
            graph.remove((s_, SDO.author, o))
            graph.add((s_, DCTERMS.creator, o))

        # contributor
        for s_, o in chain(
            graph.subject_objects(DC.contributor),
            graph.subject_objects(SDO.contributor),
        ):
            graph.remove((s_, DC.contributor, o))
            graph.remove((s_, SDO.contributor, o))
            graph.add((s_, DCTERMS.contributor, o))

        # publisher
        for s_, o in chain(
            graph.subject_objects(DC.publisher),
            graph.subject_objects(SDO.publisher),
        ):
            graph.remove((s_, DC.publisher, o))
            graph.remove((s_, SDO.publisher, o))
            graph.add((s_, DCTERMS.publisher, o))

        # indicate Agent instances from properties
        for o in chain(
            graph.objects(None, DCTERMS.publisher),
            graph.objects(None, DCTERMS.creator),
            graph.objects(None, DCTERMS.contributor),
        ):
            graph.add((o, RDF.type, PROV.Agent))

        # Agent annotations
        for s_, o in graph.subject_objects(FOAF.name):
            graph.add((s_, SDO.name, o))

        for s_, o in graph.subject_objects(FOAF.mbox):
            graph.add((s_, SDO.email, o))

        for s_, o in graph.subject_objects(ORG.memberOf):
            graph.add((s_, SDO.affiliation, o))

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
                    resources=self.__res(*this_onts_props[prop_iri], prop=prop_iri),
                )
            )

        return OntologyDefinienda(
            iri=iri,
            titles=[
                x for x in this_onts_props[DCTERMS.title] if isinstance(x, Literal)
            ],
            properties=our_props,
        )

    @cached_property
    def schema(self) -> Graph:  # noqa: PLR0912 C901
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
                        if p2 not in AGENT_PROPS:
                            continue
                        sdo.add((o, p2, o2))
                elif p_ == DCTERMS.contributor:
                    sdo.add((ont_iri, SDO.contributor, o))
                    if isinstance(o, Literal):
                        continue
                    for p2, o2 in self.__ont.predicate_objects(o):
                        if p2 not in AGENT_PROPS:
                            continue
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

    def __call__(self) -> Ontology:
        """Extract an ontology."""
        return Ontology(
            schema_json=self.schema.serialize(format="json-ld"),
            metadata=self._make_metadata(),
            sections=tuple(self.__make_sections()),
            namespaces=self.__make_namespaces(),
        )

    def __make_sections(self) -> Generator[TypeDefinienda]:
        for prop in IndexedProperty:
            if (None, RDF.type, prop.iri) not in self.__ont:
                continue

            yield self.__extract_section(prop)

    def __make_namespaces(self) -> Sequence[tuple[str, URIRef]]:
        return sorted(used_namespaces(self.__ont), key=lambda prefix_ns: prefix_ns[0])

    def __extract_section(  # noqa: C901
        self,
        prop: IndexedProperty,
    ) -> TypeDefinienda:
        """Extract information about the given section."""
        props = set(prop.properties)

        definienda: list[Definiendum] = []
        for sub in self.__ont.subjects(predicate=RDF.type, object=prop.iri):
            # TODO: Do we want to support blank node definitions?
            if not isinstance(sub, URIRef):
                continue

            # skip any specialized subtypes
            if len(prop.specializations) > 0:
                special_queries = [(sub, RDF.type, sub) for sub in prop.specializations]
                if any(q in self.__ont for q in special_queries):
                    continue

            # collect properties
            this_props: defaultdict[URIRef, list[Node]] = defaultdict(list)
            for p, o in self.__ont.predicate_objects(subject=sub):
                if p not in props:
                    continue
                if not isinstance(p, URIRef):
                    msg = "never reached: p in props is and URIRef"
                    raise TypeError(msg)

                this_props[
                    ONTDOC.restriction
                    if (
                        p == RDFS.subClassOf
                        and (o, RDF.type, OWL.Restriction) in self.__ont
                    )
                    else p
                ].append(o)

            def_props: list[PropertyResourcePair] = []
            for prop_iri in prop.properties:
                if prop_iri not in this_props:
                    continue

                nodes = this_props[prop_iri]
                def_props.append(
                    # TODO: Check if we need to pass prop_iri at all
                    # or we can remove it completely!
                    PropertyResourcePair(
                        prop=self.__meta[prop_iri],
                        resources=self.__res(*nodes, prop=prop_iri),
                    )
                )

            titles = [x for x in this_props[DCTERMS.title] if isinstance(x, Literal)]
            if len(titles) == 0:
                title = iri_to_title(sub)
                if title is not None:
                    titles = [Literal(title)]
                else:
                    titles = [Literal(prop.iri, datatype=XSD.anyURI)]

            definienda.append(
                Definiendum(
                    iri=sub,
                    prop=prop,
                    titles=titles,
                    properties=def_props,
                )
            )
        return TypeDefinienda(prop=prop, definienda=definienda)
