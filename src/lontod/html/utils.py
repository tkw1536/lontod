"""Utility functions."""

# spellchecker:words ONTDOC RDFS VANN onts trpls trpl ASGS orcid xlink evenodd uriref setclass inferencing elems specialised

from collections import defaultdict
from collections.abc import Sequence
from typing import Literal as TLiteral

from dominate.tags import (
    code,
    dd,
    div,
    dt,
    h2,
    h3,
    sup,
    table,
    td,
    th,
    tr,
)
from rdflib import Graph
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS
from rdflib.term import Node, URIRef

from .data.core import RenderContext
from .data.meta import MetaOntologies
from .extractors._rdf import (
    ONT_TYPES,
    ONTDOC,
)
from .extractors.core import iri_to_title
from .extractors.resource import ResourceExtractor


def sort_ontology(ont_orig: Graph) -> Graph:
    """Create a copy of the supplied ontology, sorted by subjects."""
    trpls = ont_orig.triples((None, None, None))
    trpls_srt = sorted(trpls)
    ont_sorted = Graph(
        bind_namespaces="core",
        namespace_manager=ont_orig.namespace_manager,
    )
    for trpl in trpls_srt:
        ont_sorted.add(trpl)
    return ont_sorted


def prop_obj_pair_html(
    ctx: RenderContext,
    ont: Graph,
    back_onts: MetaOntologies,
    table_or_dl: TLiteral["table", "dl"],
    prop_iri: URIRef,
    objs: list[Node],
    obj_type: URIRef | None = None,
) -> tr | div:
    """Make a HTML Definition for a given object pair.

    Make a HTML Definition list dt & dd pair or a Table tr, th & td set, for a given RDF property & resource pair.
    """
    prop = back_onts[prop_iri]
    res = ResourceExtractor(ont, back_onts)(*objs, rdf_type=obj_type, prop=prop_iri)

    prop_html = prop.to_html(ctx)
    res_html = res.to_html(ctx)

    return (
        tr(th(prop_html), td(res_html))
        if table_or_dl == "table"
        else div(dt(prop_html), dd(res_html))
    )


def section_html(
    ctx: RenderContext,
    section_title: str,
    ont: Graph,
    back_onts: MetaOntologies,
    obj_class: URIRef,
    prop_list: Sequence[URIRef],
    toc: dict[str, list[tuple[str, str]]],
    toc_ul_id: str,
) -> div:
    """Make all the HTML (div, title & table) for all instances of a
    given RDF class, e.g. owl:Class or owl:ObjectProperty.
    """

    def _element_html(
        ont_: Graph,
        back_onts_: MetaOntologies,
        iri: URIRef,
        fid: str,
        title_: str | None,
        ont_type: URIRef,
        props_list: Sequence[URIRef],
        this_props_: dict[URIRef, list[Node]],
    ) -> div:
        """Make all the HTML (div, title & table) for one instance of a
        given RDF class, e.g. owl:Class or owl:ObjectProperty.
        """
        d = div(
            h3(
                title_,
                sup(
                    ONT_TYPES[ont_type][0],
                    _class="sup-" + ONT_TYPES[ont_type][0],
                    title=ONT_TYPES[ont_type][1],
                ),
            ),
            id=fid,
            _class="property entity",
        )
        t = table(tr(th("IRI"), td(code(str(iri)))))
        # order the properties as per PROP_PROPS list order
        for prop in props_list:
            if prop == DCTERMS.title or prop not in this_props:
                continue

            t.appendChild(
                prop_obj_pair_html(
                    ctx,
                    ont_,
                    back_onts_,
                    "table",
                    prop,
                    this_props_[prop],
                ),
            )
        d.appendChild(t)
        return d

    elems = div(id=toc_ul_id, _class="section")
    elems.appendChild(h2(section_title))
    # get all objects of this class
    for s_ in ont.subjects(predicate=RDF.type, object=obj_class):
        if obj_class == RDF.Property:
            specialised_props = [
                (s_, RDF.type, OWL.ObjectProperty),
                (s_, RDF.type, OWL.DatatypeProperty),
                (s_, RDF.type, OWL.AnnotationProperty),
                (s_, RDF.type, OWL.FunctionalProperty),
            ]
            if any(x in ont for x in specialised_props):
                continue

        if not isinstance(s_, URIRef):
            continue

        # ignore blank nodes for things like [ owl:unionOf ( ... ) ]
        this_props: defaultdict[URIRef, list[Node]] = defaultdict(list)

        # get all properties of this object
        for p_, o in ont.predicate_objects(subject=s_):
            # ... in the property list for this class
            if p_ in prop_list:
                if not isinstance(p_, URIRef):
                    # always reached because prop_list only contains URIRefs
                    msg = "never reached"
                    raise AssertionError(msg)
                if p_ == RDFS.subClassOf and (o, RDF.type, OWL.Restriction) in ont:
                    this_props[ONTDOC.restriction].append(o)
                else:
                    this_props[p_].append(o)

        if len(this_props[DCTERMS.title]) == 0:
            this_fid = ctx.fragment(s_, None)
            this_title = iri_to_title(s_)
        else:
            # TODO: Multiple things
            this_fid = ctx.fragment(s_, this_props[DCTERMS.title][0])
            this_title = str(
                this_props[DCTERMS.title],
            )  # TODO: this isn't right #pylint: disable=fixme

        if this_title is None:
            this_title = "(No title)"

        # add to ToC
        if toc.get(toc_ul_id) is None:
            toc[toc_ul_id] = []
        toc[toc_ul_id].append(("#" + this_fid, this_title))

        # create properties table
        elems.appendChild(
            _element_html(
                ont,
                back_onts,
                s_,
                this_fid,
                this_title,
                obj_class,
                prop_list,
                this_props,
            ),
        )

    return elems


class PylodeError(Exception):
    """An error from PyLode."""
