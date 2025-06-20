"""Utility functions."""

# spellchecker:words ONTDOC RDFS VANN onts trpls trpl ASGS orcid xlink evenodd uriref setclass inferencing elems specialised

import re
from collections import defaultdict
from collections.abc import Sequence
from itertools import chain
from typing import TypeVar

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
from rdflib.namespace import DCTERMS, OWL, PROF, RDF, RDFS, SKOS, VANN
from rdflib.term import Node, URIRef

from .common import generate_fid
from .data import RenderContext
from .data_single import rdf_obj_html
from .meta import MetaOntologies
from .rdf_elements import (
    ONT_TYPES,
    ONTDOC,
)


def get_ns(ont: Graph) -> tuple[str, str]:
    """Get the default Namespace for the given graph (ontology)."""
    # if this ontology declares a preferred URI, use that
    pref_iri = None
    for _, o in ont.subject_objects(predicate=VANN.preferredNamespaceUri):
        pref_iri = str(o)

    pref_prefix = None
    for _, o in ont.subject_objects(predicate=VANN.preferredNamespacePrefix):
        pref_prefix = str(o)
    if pref_prefix is None:
        pref_prefix = ""

    if pref_iri is not None:
        return pref_prefix, pref_iri

    # if not, try the URI of the main object, compared to all prefixes
    default_iri = None

    for s_ in chain(
        ont.subjects(predicate=RDF.type, object=OWL.Ontology),
        ont.subjects(predicate=RDF.type, object=SKOS.ConceptScheme),
        ont.subjects(predicate=RDF.type, object=PROF.Profile),
    ):
        default_iri = str(s_)

    if default_iri is None:
        # can't find either a declared or default namespace
        # so we have an error
        msg = (
            "pyLODE can't detect a URI for an owl:Ontology, "
            "a skos:ConceptScheme or a prof:Profile"
        )
        raise PylodeError(
            msg,
        )

    prefix = ont.compute_qname(default_iri, True)[0]
    if prefix is None:
        msg = "compute_qname return None"
        raise AssertionError(msg)
    return prefix, default_iri


def make_title_from_iri(iri: URIRef) -> str | None:
    """Make a human-readable title for an RDF resource from its IRI."""
    if not isinstance(iri, str):
        iri = str(iri)
    # can't tolerate any URI faults so return None if anything is wrong

    # URIs with no path segments or ending in slash
    segments = iri.split("/")
    if len(segments[-1]) < 1:
        return None

    # URIs with only a domain - no path segments
    if len(segments) < 4:  # noqa: PLR2004
        return None

    # URIs ending in hash
    if segments[-1].endswith("#"):
        return None

    id_part = (
        segments[-1].split("#")[-1]
        if segments[-1].split("#")[-1] != ""
        else segments[-1].split("#")[-2]
    )

    # split CamelCase
    # title case if the first char is uppercase (likely a Class)
    # else lower (property/Named Individual)
    words = re.split(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", id_part)
    if words[0][0].isupper():
        return " ".join(words).title()
    return " ".join(words).lower()


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


_GLOBAL_RENDER_CONTEXT = RenderContext()


def prop_obj_pair_html(
    ont: Graph,
    back_onts: MetaOntologies,
    ns: tuple[str, str],
    table_or_dl: str,
    prop_iri: URIRef,
    fids: dict[str, str],
    obj: list[Node],
    obj_type: URIRef | None = None,
) -> tr | div:
    """Make a HTML Definition for a given object pair.

    Make a HTML Definition list dt & dd pair or a Table tr, th & td set, for a given RDF property & resource pair.
    """
    prop = back_onts[prop_iri].to_html(_GLOBAL_RENDER_CONTEXT)
    o = rdf_obj_html(ont, back_onts, ns, obj, fids, rdf_type=obj_type, prop=prop_iri)

    return tr(th(prop), td(o)) if table_or_dl == "table" else div(dt(prop), dd(o))


def section_html(
    section_title: str,
    ont: Graph,
    back_onts: MetaOntologies,
    ns: tuple[str, str],
    obj_class: URIRef,
    prop_list: Sequence[URIRef],
    toc: dict[str, list[tuple[str, str]]],
    toc_ul_id: str,
    fids: dict[str, str],
) -> div:
    """Make all the HTML (div, title & table) for all instances of a
    given RDF class, e.g. owl:Class or owl:ObjectProperty.
    """

    def _element_html(
        ont_: Graph,
        back_onts_: MetaOntologies,
        ns_: tuple[str, str],
        iri: URIRef,
        fid: str,
        title_: str | None,
        ont_type: URIRef,
        props_list: Sequence[URIRef],
        this_props_: dict[URIRef, list[Node]],
        fids_: dict[str, str],
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
                    ont_,
                    back_onts_,
                    ns_,
                    "table",
                    prop,
                    fids_,
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
            this_fid = generate_fid(None, s_, fids)
            this_title = make_title_from_iri(s_)
        else:
            this_fid = generate_fid(this_props[DCTERMS.title][0], s_, fids)
            this_title = str(
                this_props[DCTERMS.title],
            )  # TODO: this isn't right #pylint: disable=fixme

        if this_fid is None:
            msg = "wasn't able to generate fid"
            raise AssertionError(msg)

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
                ns,
                s_,
                this_fid,
                this_title,
                obj_class,
                prop_list,
                this_props,
                fids,
            ),
        )

    return elems


T = TypeVar("T")


class PylodeError(Exception):
    """An error from PyLode."""
