"""rendering a single object"""

from typing import List, Optional, Tuple, Union, cast

import markdown  # type: ignore
from dominate.tags import (  # type: ignore
    a,
    br,
    em,
    html_tag,
    li,
    pre,
    span,
    sup,
    ul,
)
from dominate.util import raw  # type: ignore
from rdflib import Graph
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, SDO, SKOS
from rdflib.paths import ZeroOrMore
from rdflib.term import BNode, Literal, Node, URIRef

from .common import generate_fid, intersperse, must_uriref
from .meta import MetaOntologies
from .rdf_elements import (
    AGENT_PROPS,
    ONT_TYPES,
    OWL_SET_TYPES,
    RESTRICTION_TYPES,
)


def _rdf_obj_html(
    ont: Graph,
    back_onts: MetaOntologies,
    ns: Tuple[str, str],
    obj: List[Node],
    fids: dict[str, str],
    rdf_type: URIRef | None = None,
    prop: URIRef | None = None,
) -> ul:
    """Makes a sensible HTML rendering of an RDF resource.

    Can handle IRIs, Blank Nodes of Agents or OWL Restrictions or Literals"""

    def _rdf_obj_single_html(
        ont_: Graph,
        back_onts_: MetaOntologies,
        ns_: Tuple[str, str],
        obj_: Node,
        fids_: dict[str, str],
        rdf_type_: Optional[URIRef] = None,
        prop: URIRef | None = None,
    ) -> ul:
        def _hyperlink_html(
            ont__: Graph,
            back_onts__: MetaOntologies,
            ns__: Tuple[str, str],
            iri__: URIRef,
            fids__: dict[str, str],
            rdf_type__: Optional[URIRef] = None,
        ) -> span | a:
            if (iri__, RDF.type, PROV.Agent) in ont__:
                return _agent_html(ont__, iri__)

            def _get_ont_type(
                ont___: Graph, back_onts___: MetaOntologies, iri___: Node
            ) -> URIRef | None:
                types_we_know = [
                    OWL.Class,
                    OWL.ObjectProperty,
                    OWL.DatatypeProperty,
                    OWL.AnnotationProperty,
                    OWL.FunctionalProperty,
                    RDF.Property,
                ]

                this_objects_types = []
                for o in ont___.objects(iri___, RDF.type):
                    if o in ONT_TYPES:
                        this_objects_types.append(o)

                for x_ in types_we_know:
                    if x_ in this_objects_types:
                        return x_

                for o in back_onts___.types_of(iri__):
                    if o in ONT_TYPES:
                        this_objects_types.append(o)

                for x_ in types_we_know:
                    if x_ in this_objects_types:
                        return x_

                return None

            # find type
            if rdf_type__ is None:
                rdf_type__ = _get_ont_type(ont__, back_onts__, iri__)

            # if it's a thing in this ontology, use a fragment link
            frag_iri = None
            if ns__ is not None and str(iri__).startswith(ns__):
                fid = generate_fid(None, iri__, fids__)
                if fid is not None:
                    frag_iri = "#" + fid

            # use the objet's label for hyperlink text, if it has one
            # if not, try and use a prefixed hyperlink
            # if not, just the iri
            v: Node | None = back_onts__.title_of(iri__)

            # no need to check other labels: inference
            if v is None:
                v = ont__.value(subject=iri__, predicate=DCTERMS.title)
            if v is not None:
                anchor = a(f"{v}", href=frag_iri if frag_iri is not None else iri__)
            else:
                qname: URIRef | tuple[str, URIRef, str]
                try:
                    qname = ont__.compute_qname(iri__, False)
                    if "ASGS" in qname[2]:
                        print(qname)
                except Exception:
                    qname = iri__
                prefix = "" if qname[0] == "" else f"{qname[0]}:"

                if isinstance(qname, tuple):
                    anchor = a(
                        f"{prefix}{qname[2]}",
                        href=frag_iri if frag_iri is not None else iri__,
                    )
                else:
                    anchor = a(
                        f"{qname}", href=frag_iri if frag_iri is not None else iri__
                    )

            if rdf_type__ is None:
                return anchor

            ret = span()
            ret.appendChild(anchor)
            ret.appendChild(
                sup(
                    ONT_TYPES[rdf_type__][0],
                    _class="sup-" + ONT_TYPES[rdf_type__][0],
                    title=ONT_TYPES[rdf_type__][1],
                )
            )
            return ret

        def _literal_html(obj__: Union[URIRef, BNode, Literal]) -> html_tag:
            if str(obj__).startswith("http"):
                return _hyperlink_html(
                    ont_, back_onts_, ns_, cast(URIRef, obj__), fids_
                )

            if prop == SKOS.example:
                return pre(str(obj__))

            return raw(markdown.markdown(str(obj__)))

        def _agent_html(ont__: Graph, obj__: Union[URIRef, BNode, Literal]) -> html_tag:
            def _affiliation_html(
                ont___: Graph, obj___: Union[URIRef, BNode, Literal]
            ) -> html_tag:
                name_ = None
                url_ = None

                for p_, o_ in ont___.predicate_objects(obj___):
                    if p_ in AGENT_PROPS:
                        if p_ == SDO.name:
                            name_ = str(o_)
                        elif p_ == SDO.url:
                            url_ = str(o_)

                sp_ = span()
                if name_ is not None:
                    if url_ is not None:
                        sp_.appendChild(em(" of ", a(name_, href=url_)))
                    else:
                        sp_.appendChild(em(" of ", name_))
                else:
                    if "http" in obj___:
                        sp_.appendChild(em(" of ", a(obj___, href=obj___)))
                return sp_

            if isinstance(obj__, Literal):
                return span(str(obj__))
            honorific_prefix = None
            name = None
            identifier = None
            orcid = None
            orcid_logo = """
                    <svg width="15px" height="15px" viewBox="0 0 72 72" version="1.1"
                        xmlns="http://www.w3.org/2000/svg"
                        xmlns:xlink="http://www.w3.org/1999/xlink">
                        <title>Orcid logo</title>
                        <g id="Symbols" stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
                            <g id="hero" transform="translate(-924.000000, -72.000000)" fill-rule="nonzero">
                                <g id="Group-4">
                                    <g id="vector_iD_icon" transform="translate(924.000000, 72.000000)">
                                        <path d="M72,36 C72,55.884375 55.884375,72 36,72 C16.115625,72 0,55.884375 0,36 C0,16.115625 16.115625,0 36,0 C55.884375,0 72,16.115625 72,36 Z" id="Path" fill="#A6CE39"></path>
                                        <g id="Group" transform="translate(18.868966, 12.910345)" fill="#FFFFFF">
                                            <polygon id="Path" points="5.03734929 39.1250878 0.695429861 39.1250878 0.695429861 9.14431787 5.03734929 9.14431787 5.03734929 22.6930505 5.03734929 39.1250878"></polygon>
                                            <path d="M11.409257,9.14431787 L23.1380784,9.14431787 C34.303014,9.14431787 39.2088191,17.0664074 39.2088191,24.1486995 C39.2088191,31.846843 33.1470485,39.1530811 23.1944669,39.1530811 L11.409257,39.1530811 L11.409257,9.14431787 Z M15.7511765,35.2620194 L22.6587756,35.2620194 C32.49858,35.2620194 34.7541226,27.8438084 34.7541226,24.1486995 C34.7541226,18.1301509 30.8915059,13.0353795 22.4332213,13.0353795 L15.7511765,13.0353795 L15.7511765,35.2620194 Z" id="Shape"></path>
                                            <path d="M5.71401206,2.90182329 C5.71401206,4.441452 4.44526937,5.72914146 2.86638958,5.72914146 C1.28750978,5.72914146 0.0187670918,4.441452 0.0187670918,2.90182329 C0.0187670918,1.33420133 1.28750978,0.0745051096 2.86638958,0.0745051096 C4.44526937,0.0745051096 5.71401206,1.36219458 5.71401206,2.90182329 Z" id="Path"></path>
                                        </g>
                                    </g>
                                </g>
                            </g>
                        </g>
                    </svg>"""
            url = None
            email = None
            affiliation = None

            if "orcid.org" in str(obj__):
                orcid = True

            for px, o in ont__.predicate_objects(obj__):
                if px in AGENT_PROPS:
                    if px == SDO.name:
                        name = str(o)
                    elif px == SDO.honorificPrefix:
                        honorific_prefix = str(o)
                    elif px == SDO.identifier:
                        identifier = str(o)
                        if "orcid.org" in str(o):
                            orcid = True
                    elif px == SDO.url:
                        url = str(o)
                    elif px == SDO.email:
                        email = str(o)
                    elif px == SDO.affiliation and isinstance(
                        o, (URIRef, BNode, Literal)
                    ):
                        affiliation = o

            sp = span()

            if name is not None:
                if honorific_prefix is not None:
                    name = honorific_prefix + " " + name

                if url is not None:
                    sp.appendChild(a(name, href=url))
                else:
                    sp.appendChild(span(name))

                if orcid:
                    if "orcid.org" in obj__:
                        sp.appendChild(a(raw(orcid_logo), href=obj__))
                    else:
                        sp.appendChild(a(raw(orcid_logo), href=identifier))
                elif identifier is not None:
                    sp.appendChild(a(identifier, href=identifier))
                if email is not None:
                    email = email.replace("mailto:", "")
                    sp.appendChild(span("(", a(email, href="mailto:" + email), " )"))

                if affiliation is not None:
                    sp.appendChild(_affiliation_html(ont__, affiliation))
            else:
                if not orcid:
                    return obj__
                return sp.appendChild(a(obj__, href=obj__))
            return sp

        def _restriction_html(
            ont__: Graph, obj__: Node, ns__: tuple[str, str]
        ) -> html_tag:
            prop = None
            card = None
            cls = None

            for px, o in ont__.predicate_objects(obj__):
                if px == RDF.type:
                    continue
                if px == OWL.onProperty:
                    prop = _hyperlink_html(
                        ont__, back_onts_, ns__, must_uriref(o), fids_
                    )
                elif px in RESTRICTION_TYPES + OWL_SET_TYPES:
                    if px in [
                        OWL.minCardinality,
                        OWL.minQualifiedCardinality,
                        OWL.maxCardinality,
                        OWL.maxQualifiedCardinality,
                        OWL.cardinality,
                        OWL.qualifiedCardinality,
                    ]:
                        if px in [OWL.minCardinality, OWL.minQualifiedCardinality]:
                            card = "min"
                        elif px in [
                            OWL.maxCardinality,
                            OWL.maxQualifiedCardinality,
                        ]:
                            card = "max"
                        elif px in [OWL.cardinality, OWL.qualifiedCardinality]:
                            card = "exactly"

                        card = span(span(card, _class="cardinality"), span(str(o)))
                    else:
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

                            card = span(
                                span(card, _class="cardinality"),
                                raw(_rdf_obj_single_html),
                            )

                        card = span(
                            span(card, _class="cardinality"),
                            span(
                                _hyperlink_html(
                                    ont__,
                                    back_onts_,
                                    ns__,
                                    must_uriref(o),
                                    fids_,
                                    OWL.Class,
                                )
                            ),
                        )

            restriction = span(prop, card, br()) if card is not None else prop
            restriction = (
                span(restriction, cls, br()) if cls is not None else restriction
            )

            return span(restriction) if restriction is not None else "None"

        def _setclass_html(
            ont__: Graph,
            obj__: Node,
            back_onts__: MetaOntologies,
            ns__: Tuple[str, str],
            fids__: dict[str, str],
        ) -> list[html_tag]:
            """Makes lists of (union) 'ClassX or Class Y or ClassZ' or
            (intersection) 'ClassX and Class Y and ClassZ'"""

            joining_word: html_tag
            if (obj__, OWL.unionOf, None) in ont__:
                joining_word = span("or", _class="cardinality")
            elif (obj__, OWL.intersectionOf, None) in ont__:
                joining_word = span("and", _class="cardinality")
            else:
                joining_word = span(",", _class="cardinality")

            class_set = set()  # type: set[html_tag]
            for o in ont__.objects(obj__, OWL.unionOf | OWL.intersectionOf):
                # TODO How does this work?
                for o2 in ont__.objects(o, RDF.rest * ZeroOrMore / RDF.first):  # type: ignore
                    class_set.add(
                        _rdf_obj_single_html(
                            ont__, back_onts__, ns__, o2, fids__, OWL.Class
                        )
                    )

            return intersperse(class_set, joining_word)

        def _bn_html(
            ont__: Graph,
            back_onts__: MetaOntologies,
            ns__: Tuple[str, str],
            fids__: dict[str, str],
            obj__: BNode,
        ) -> html_tag | list[html_tag]:
            # TODO: remove back_onts and fids if not needed by subfunctions #pylint: disable=fixme
            # What kind of BN is it?
            # An Agent, a Restriction or a Set Class (union/intersection)
            # handled all typing added in OntDoc inferencing
            if (obj__, RDF.type, PROV.Agent) in ont__:
                return _agent_html(ont__, obj__)
            if (obj__, RDF.type, OWL.Restriction) in ont__:
                return _restriction_html(ont__, obj__, ns__)

            # (obj, RDF.type, OWL.Class) in ont:  # Set Class
            return _setclass_html(ont__, obj__, back_onts__, ns__, fids__)

        if isinstance(obj_, (URIRef, tuple)):
            ret = _hyperlink_html(
                ont_, back_onts_, ns_, obj_, fids_, rdf_type__=rdf_type_
            )
        elif isinstance(obj_, BNode):
            ret = _bn_html(ont_, back_onts_, ns_, fids_, obj_)
        elif isinstance(obj_, Literal):
            ret = _literal_html(obj_)
        else:
            raise AssertionError("never reached")

        return ret if ret is not None else span()

    if len(obj) == 1:
        return _rdf_obj_single_html(
            ont, back_onts, ns, obj[0], fids, rdf_type_=rdf_type, prop=prop
        )

    u_ = ul()
    for x in obj:
        u_.appendChild(
            li(
                _rdf_obj_single_html(
                    ont, back_onts, ns, x, fids, rdf_type_=rdf_type, prop=prop
                )
            )
        )
    return u_
