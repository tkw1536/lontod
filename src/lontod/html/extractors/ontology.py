"""extracting information about an ontology as a whole."""

from collections import defaultdict

from rdflib import Graph
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, XSD
from rdflib.term import Literal, Node, URIRef

from lontod.html.data._rdf import ONTDOC, PropertyKind
from lontod.html.data.meta import MetaOntologies
from lontod.html.data.ontology import (
    Definiendum,
    PropertyResourcePair,
    TypeDefinienda,
)
from lontod.html.extractors.core import iri_to_title
from lontod.html.extractors.resource import ResourceExtractor


class OntologyExtractor:
    """Extracts information about a single ontology."""

    def __init__(
        self, ont: Graph, meta: MetaOntologies, res: ResourceExtractor
    ) -> None:
        """Create a new ontology extractor."""
        self.ont = ont
        self.meta = meta
        self.res = res

    def extract(
        self,
        rdf_type: PropertyKind,
    ) -> TypeDefinienda:
        """Extract information about the given section."""
        iri, info = rdf_type.uri, rdf_type.info
        specials = info.specializations
        props = set(info.properties)

        definienda: list[Definiendum] = []
        for sub in self.ont.subjects(predicate=RDF.type, object=iri):
            # TODO: Do we want to support blank node definitions?
            if not isinstance(sub, URIRef):
                continue

            # skip any specialized subtypes
            if len(specials) > 0:
                special_queries = [(sub, RDF.type, sub) for sub in specials]
                if any(q in self.ont for q in special_queries):
                    continue

            # collect properties
            this_props: defaultdict[URIRef, list[Node]] = defaultdict(list)
            for p, o in self.ont.predicate_objects(subject=sub):
                if p not in props:
                    continue
                if not isinstance(p, URIRef):
                    msg = "never reached: p in props is and URIRef"
                    raise TypeError(msg)

                this_props[
                    ONTDOC.restriction
                    if (
                        p == RDFS.subClassOf
                        and (o, RDF.type, OWL.Restriction) in self.ont
                    )
                    else p
                ].append(o)

            def_props: list[PropertyResourcePair] = []
            for prop_iri in info.properties:
                if prop_iri == DCTERMS.title or prop_iri not in this_props:
                    continue

                nodes = this_props[prop_iri]
                def_props.append(
                    # TODO: Check if we need to pass prop_iri at all
                    # or we can remove it completely!
                    PropertyResourcePair(
                        prop=self.meta[prop_iri],
                        resources=self.res(*nodes, rdf_type=rdf_type, prop=prop_iri),
                    )
                )

            titles = [x for x in this_props[DCTERMS.title] if isinstance(x, Literal)]
            if len(titles) == 0:
                title = iri_to_title(sub)
                if title is not None:
                    titles = [Literal(title)]
                else:
                    titles = [Literal(iri, datatype=XSD.anyURI)]

            definienda.append(
                Definiendum(
                    iri=sub,
                    rdf_type=rdf_type,
                    titles=titles,
                    props=def_props,
                )
            )
        return TypeDefinienda(rdf_type=rdf_type, definienda=definienda)
