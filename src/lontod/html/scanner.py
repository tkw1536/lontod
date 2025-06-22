"""parses an ontology as html."""

from collections import defaultdict
from collections.abc import Generator
from importlib import resources
from itertools import chain
from typing import cast

import dominate
from dominate.tags import (
    a,
    code,
    dd,
    div,
    dl,
    dt,
    h1,
    h2,
    h3,
    h4,
    html_tag,
    li,
    meta,
    script,
    strong,
    style,
    sup,
    table,
    td,
    tr,
    ul,
)
from dominate.util import raw
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

from .data.core import HTMLable, RenderContext
from .extractors._rdf import (
    AGENT_PROPS,
    CLASS_PROPS,
    ONT_PROPS,
    ONTDOC,
    PROP_PROPS,
)
from .extractors.meta import MetaExtractor
from .utils import (
    PylodeError,
    prop_obj_pair_html,
    section_html,
    sort_ontology,
)

# spellchecker:words ONTDOC FOAF RDFS onts Helper objectproperties datatypeproperties annotationproperties functionalproperties nses


class Ontology(HTMLable):
    """Ontology Document class used to create HTML documentation
    from OWL Ontologies.
    """

    def __init__(self, ontology: Graph) -> None:
        """Create a new Ontology."""
        self.__ont = sort_ontology(ontology)
        self._ontdoc_inference(self.__ont)

        self.__meta = MetaExtractor()()
        self.__toc: dict[str, list[tuple[str, str]]] = {}

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

    @property
    def title(self) -> Literal:
        """Title of this ontology."""
        for s in chain(
            self.__ont.subjects(RDF.type, OWL.Ontology),
            self.__ont.subjects(RDF.type, PROF.Profile),
            self.__ont.subjects(RDF.type, SKOS.ConceptScheme),
        ):
            for o2 in self.__ont.objects(s, DCTERMS.title):
                if not isinstance(o2, Literal):
                    continue
                return o2

        msg = (
            "You MUST supply a title property "
            "(dcterms:title, rdfs:label or sdo:name) for your ontology"
        )
        raise PylodeError(
            msg,
        )

    def to_html(self, ctx: RenderContext) -> dominate.document:
        """Render this ontology into a document."""
        doc = dominate.document(title=self.title)

        with doc.head:
            for tag in self._head():
                tag.render()

        body = self._make_body(ctx)
        doc.appendChild(body)

        return doc

    def render(self) -> str:
        """Render this document into a string."""
        res = self.to_html(RenderContext()).render(pretty=True)
        return cast("str", res)

    def _head(
        self,
    ) -> Generator[html_tag]:
        """Make <head>???</head> content."""
        css = resources.files(__package__).joinpath("assets", "style.css").read_text()
        yield style(raw("\n" + css + "\n\t"))

        yield meta(http_equiv="Content-Type", content="text/html; charset=utf-8")

        yield script(
            raw("\n" + self.schema.serialize(format="json-ld") + "\n\t"),
            type="application/ld+json",
            id="schema.org",
        )

    def _make_body(self, ctx: RenderContext) -> html_tag:
        """Make <body>???</body> content.

        Just calls other helper functions in order.
        """
        content = div(id="content")

        for tag in chain(
            self._make_metadata(ctx),
            self._make_main_sections(ctx),
            self._make_namespaces(),
            self._make_legend(),
            self._make_toc(),
        ):
            content.appendChild(tag)

        return content

    def _make_metadata(self, ctx: RenderContext) -> Generator[html_tag]:
        # get all ONT_PROPS props and their (multiple) values
        this_onts_props: defaultdict[URIRef, list[Node]] = defaultdict(list)
        for s_ in chain(
            self.__ont.subjects(predicate=RDF.type, object=OWL.Ontology),
            self.__ont.subjects(predicate=RDF.type, object=SKOS.ConceptScheme),
            self.__ont.subjects(predicate=RDF.type, object=PROF.Profile),
        ):
            iri = s_
            for p_, o in self.__ont.predicate_objects(s_):
                if p_ not in ONT_PROPS:
                    continue
                if not isinstance(p_, URIRef):
                    # always True because ONT_PROPS only has URIRefs
                    msg = "never reached"
                    raise TypeError(msg)
                this_onts_props[p_].append(o)

        # make HTML for all props in order of ONT_PROPS
        sec = div(h1(this_onts_props[DCTERMS.title]), id="metadata", _class="section")
        sec.appendChild(h2("Metadata"))
        d = dl(div(dt(strong("IRI")), dd(code(str(iri)))))
        for prop in ONT_PROPS:
            if prop in this_onts_props:
                d.appendChild(
                    prop_obj_pair_html(
                        ctx,
                        self.__ont,
                        self.__meta,
                        "dl",
                        prop,
                        this_onts_props[prop],
                    ),
                )
        sec.appendChild(d)
        yield sec

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

    def _make_main_sections(self, ctx: RenderContext) -> Generator[html_tag]:
        if (None, RDF.type, OWL.Class) in self.__ont:
            yield section_html(
                ctx,
                "Classes",
                self.__ont,
                self.__meta,
                OWL.Class,
                CLASS_PROPS,
                self.__toc,
                "classes",
            )

        if (
            None,
            RDF.type,
            RDF.Property,
        ) in self.__ont:
            yield section_html(
                ctx,
                "Properties",
                self.__ont,
                self.__meta,
                RDF.Property,
                PROP_PROPS,
                self.__toc,
                "properties",
            )

        if (None, RDF.type, OWL.ObjectProperty) in self.__ont:
            yield section_html(
                ctx,
                "Object Properties",
                self.__ont,
                self.__meta,
                OWL.ObjectProperty,
                PROP_PROPS,
                self.__toc,
                "objectproperties",
            )

        if (None, RDF.type, OWL.DatatypeProperty) in self.__ont:
            yield section_html(
                ctx,
                "Datatype Properties",
                self.__ont,
                self.__meta,
                OWL.DatatypeProperty,
                PROP_PROPS,
                self.__toc,
                "datatypeproperties",
            )

        if (None, RDF.type, OWL.AnnotationProperty) in self.__ont:
            yield section_html(
                ctx,
                "Annotation Properties",
                self.__ont,
                self.__meta,
                OWL.AnnotationProperty,
                PROP_PROPS,
                self.__toc,
                "annotationproperties",
            )

        if (None, RDF.type, OWL.FunctionalProperty) in self.__ont:
            yield section_html(
                ctx,
                "Functional Properties",
                self.__ont,
                self.__meta,
                OWL.FunctionalProperty,
                PROP_PROPS,
                self.__toc,
                "functionalproperties",
            )

    def _make_legend(self) -> Generator[html_tag]:
        legend = div(id="legend")
        with legend:
            h2("Legend")
            with table(_class="entity"):
                if self.__toc.get("classes") is not None:
                    with tr():
                        td(sup("c", _class="sup-c", title="OWL/RDFS Class"))
                        td("Classes")
                if self.__toc.get("properties") is not None:
                    with tr():
                        td(sup("p", _class="sup-p", title="RDF Property"))
                        td("Properties")
                if self.__toc.get("objectproperties") is not None:
                    with tr():
                        td(sup("op", _class="sup-op", title="OWL Object Property"))
                        td("Object Properties")
                if self.__toc.get("datatypeproperties") is not None:
                    with tr():
                        td(
                            sup(
                                "dp",
                                _class="sup-dp",
                                title="OWL Datatype Property",
                            ),
                        )
                        td("Datatype Properties")
                if self.__toc.get("annotationproperties") is not None:
                    with tr():
                        td(
                            sup(
                                "ap",
                                _class="sup-ap",
                                title="OWL Annotation Property",
                            ),
                        )
                        td("Annotation Properties")
                if self.__toc.get("functionalproperties") is not None:
                    with tr():
                        td(
                            sup(
                                "fp",
                                _class="sup-fp",
                                title="OWL Functional Property",
                            ),
                        )
                        td("Functional Properties")
                if self.__toc.get("named_individuals") is not None:
                    with tr():
                        td(sup("ni", _class="sup-ni", title="OWL Named Individual"))
                        td("Named Individuals")
        yield legend

    def _make_namespaces(self) -> Generator[html_tag]:
        # only get namespaces used in ont
        nses = {}
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

        # # deduplicate namespaces
        # temp = []
        # res = dict()
        # for k, v in nses.items():
        #     if v not in temp:
        #         temp.append(v)
        #         res[k] = v
        # nses = res

        namespaces = div(id="namespaces")
        with namespaces:
            h2("Namespaces")
            with dl():
                if self.__toc.get("namespaces") is None:
                    self.__toc["namespaces"] = []
                for prefix, ns in sorted(nses.items()):
                    p_ = prefix if prefix != "" else ":"
                    dt(p_, id=p_)
                    dd(code(ns))
                    self.__toc["namespaces"].append(("#" + prefix, prefix))
        yield namespaces

    def _make_toc(self) -> Generator[html_tag]:
        toc = div(id="toc")
        with toc:
            h3("Table of Contents")
            with ul(_class="first"):
                li(h4(a("Metadata", href="#metadata")))

                if (
                    self.__toc.get("classes") is not None
                    and len(self.__toc["classes"]) > 0
                ):
                    with li():
                        h4(a("Classes", href="#classes"))
                        with ul(_class="second"):
                            for c in self.__toc["classes"]:
                                li(a(c[1], href=c[0]))

                if (
                    self.__toc.get("properties") is not None
                    and len(self.__toc["properties"]) > 0
                ):
                    with li():
                        h4(a("Properties", href="#properties"))
                        with ul(_class="second"):
                            for c in self.__toc["properties"]:
                                li(a(c[1], href=c[0]))

                if (
                    self.__toc.get("objectproperties") is not None
                    and len(self.__toc["objectproperties"]) > 0
                ):
                    with li():
                        h4(a("Object Properties", href="#objectproperties"))
                        with ul(_class="second"):
                            for c in self.__toc["objectproperties"]:
                                li(a(c[1], href=c[0]))

                if (
                    self.__toc.get("datatypeproperties") is not None
                    and len(self.__toc["datatypeproperties"]) > 0
                ):
                    with li():
                        h4(a("Datatype Properties", href="#datatypeproperties"))
                        with ul(_class="second"):
                            for c in self.__toc["datatypeproperties"]:
                                li(a(c[1], href=c[0]))

                if (
                    self.__toc.get("annotationproperties") is not None
                    and len(self.__toc["annotationproperties"]) > 0
                ):
                    with li():
                        h4(a("Annotation Properties", href="#annotationproperties"))
                        with ul(_class="second"):
                            for c in self.__toc["annotationproperties"]:
                                li(a(c[1], href=c[0]))

                if (
                    self.__toc.get("functionalproperties") is not None
                    and len(self.__toc["functionalproperties"]) > 0
                ):
                    with li():
                        h4(a("Functional Properties", href="#functionalproperties"))
                        with ul(_class="second"):
                            for c in self.__toc["functionalproperties"]:
                                li(a(c[1], href=c[0]))

                with li():
                    h4(a("Namespaces", href="#namespaces"))
                    with ul(_class="second"):
                        for n in self.__toc["namespaces"]:
                            li(a(n[1], href="#" + n[1]))

                li(h4(a("Legend", href="#legend")), ul(_class="second"))
        yield toc
