"""Dataclasses describing the ontology itself."""

from abc import ABC
from collections import defaultdict
from collections.abc import Generator, Sequence
from dataclasses import dataclass
from functools import cached_property
from importlib import resources
from typing import final, override

from rdflib.term import URIRef

from lontod.html import (
    BODY,
    CODE,
    DD,
    DIV,
    DL,
    DT,
    H1,
    H2,
    H3,
    H4,
    HEAD,
    HTML,
    LI,
    META,
    SCRIPT,
    SECTION,
    SPAN,
    STRONG,
    STYLE,
    SUP,
    TABLE,
    TD,
    TH,
    TITLE,
    TR,
    UL,
    A,
    NodeLike,
    RawNode,
)

from .core import HTMLable, RenderContext
from .meta import MetaProperty
from .rdf import LONTOD, IndexedProperty
from .resource import RDFResources

# TODO: ensure it's a sequence everywhere


@final
@dataclass(frozen=True)
class PropertyResourcePair:
    """a pair of information about a property and its' values."""

    prop: MetaProperty
    resources: RDFResources


@dataclass(frozen=True)
class _DefiniendumLike(ABC):
    iri: URIRef
    properties: Sequence[PropertyResourcePair]


@final
@dataclass(frozen=True)
class Definiendum(_DefiniendumLike, HTMLable):
    """something being defined in the ontology."""

    prop: IndexedProperty

    @override
    def to_html(self, ctx: RenderContext) -> NodeLike:
        return DIV(
            H3(
                SPAN(CODE(ctx.format_iri(self.iri))),
                " ",
                SUP(
                    self.prop.abbrev,
                    _class=f"sup-{self.prop.abbrev}",
                    title=self.prop.inline_title,
                ),
            ),
            TABLE(
                TR(
                    TH("IRI"),
                    TD(CODE(str(self.iri))),
                ),
                (
                    TR(TH(pair.prop.to_html(ctx)), TD(pair.resources.to_html(ctx)))
                    for pair in self.properties
                ),
            ),
            id=ctx.fragment(self.iri),
            _class="property entity",
        )


@dataclass(frozen=True)
class OntologyDefinienda(_DefiniendumLike, HTMLable):
    """Definienda about the ontology as a whole."""

    @override
    def to_html(self, ctx: RenderContext) -> NodeLike:
        metadata_id = ctx.fragment(LONTOD.Metadata, group="section")

        return DIV(
            H1(self.iri),
            H2("Metadata"),
            DL(
                DIV(
                    DT(STRONG("IRI")),
                    DD(CODE(str(self.iri))),
                ),
                (
                    DIV(
                        DT(pair.prop.to_html(ctx)),
                        DD(pair.resources.to_html(ctx)),
                    )
                    for pair in self.properties
                ),
            ),
            id=metadata_id,
            _class="section metadata",
        )


@dataclass(frozen=True)
class TypeDefinienda(HTMLable):
    """Definienda of a specific type."""

    prop: IndexedProperty
    definienda: Sequence[Definiendum]

    @override
    def to_html(self, ctx: RenderContext) -> NodeLike:
        return SECTION(
            H2(self.prop.plural_title),
            (definiendum.to_html(ctx) for definiendum in self.definienda),
            id=ctx.fragment(self.prop.iri, group="section"),
            _class="section classes",
        )


@dataclass(frozen=True)
class Ontology(HTMLable):
    """Data about an entire ontology."""

    schema_json: str  # TODO: re-consider this
    metadata: OntologyDefinienda
    sections: Sequence[TypeDefinienda]
    namespaces: Sequence[tuple[str, URIRef]]

    @cached_property
    def __definienda(self) -> dict[URIRef, list[Definiendum]]:
        defs: dict[URIRef, list[Definiendum]] = defaultdict(list)
        for sec in self.sections:
            for definiendum in sec.definienda:
                defs[definiendum.iri].append(definiendum)
        return defs

    def __iter__(self) -> Generator[Definiendum]:
        """Iterate through all definienda in this ontology."""
        for sec in self.sections:
            yield from sec.definienda

    def __call__(self, iri: URIRef) -> Generator[Definiendum]:
        """Return the definienda for the given URIRef."""
        yield from self.__definienda[iri]

    def __getitem__(self, iri: URIRef) -> Definiendum | None:
        """Return the first Definiendum for the given IRI or None."""
        try:
            return self.__definienda[iri][0]
        except IndexError:
            return None

    @override
    def to_html(self, ctx: RenderContext) -> NodeLike:
        return HTML(
            self.__head(),
            self.__body(ctx),
        )

    def __head(
        self,
    ) -> NodeLike:
        """Make <head>???</head> content."""
        css = resources.files(__package__).joinpath("assets", "style.css").read_text()

        return HEAD(
            TITLE(str(self.metadata.iri)),
            STYLE(RawNode("\n" + css + "\n\t")),
            META(http_equiv="Content-Type", content="text/html; charset=utf-8"),
            SCRIPT(
                RawNode("\n" + self.schema_json + "\n\t"),
                type="application/ld+json",
                id="schema.org",
            ),
        )

    def __body(self, ctx: RenderContext) -> NodeLike:
        return BODY(
            DIV(
                self.metadata.to_html(ctx),
                (s.to_html(ctx) for s in self.sections),
                self._make_namespaces(ctx),
                self._make_legend(ctx),
                self._make_toc(ctx),
                id="content",
            )
        )

    def _make_legend(self, ctx: RenderContext) -> NodeLike:
        if len(self.sections) == 0:
            return None

        legend_id = ctx.fragment(LONTOD.Legend, group="section")

        return DIV(
            H2("Legend", id=legend_id),
            TABLE(
                (
                    TR(
                        TD(
                            SUP(
                                sec.prop.abbrev,
                                _class="sup-" + sec.prop.abbrev,
                                title=sec.prop.inline_title,
                            )
                        ),
                        TD(sec.prop.plural_title),
                    )
                    for sec in self.sections
                    if len(sec.definienda) > 0
                ),
                _class="entity",
            ),
            _class="legend",
        )

    def _make_namespaces(self, ctx: RenderContext) -> NodeLike:
        if len(self.namespaces) == 0:
            return None

        namespace_id = ctx.fragment(LONTOD.Namespaces, group="section")

        return DIV(
            H2("Namespaces"),
            DL(
                (DT(prefix if prefix != "" else ":"), DD(CODE(ns)))
                for prefix, ns in self.namespaces
            ),
            id=namespace_id,
        )

    def _make_toc(self, ctx: RenderContext) -> NodeLike:
        metadata_id = ctx.fragment(LONTOD.Metadata, group="section")

        children: list[NodeLike] = [
            LI(
                H4(
                    A(
                        "Metadata",
                        href="#" + metadata_id,
                    )
                )
            ),
        ]

        for sec in self.sections:
            if len(sec.definienda) == 0:
                continue

            defs: list[NodeLike] = []
            for definiendum in sec.definienda:
                href = "#" + ctx.fragment(definiendum.iri)
                defs.append(LI(A(ctx.format_iri(definiendum.iri), href=href)))

            children.append(
                LI(
                    H4(
                        A(
                            sec.prop.plural_title,
                            href="#" + ctx.fragment(sec.prop.iri, group="section"),
                        )
                    ),
                    UL(
                        defs,
                        _class="second",
                    ),
                )
            )

        if len(self.namespaces) > 0:
            namespace_id = ctx.fragment(LONTOD.Namespaces, group="section")
            children.append(
                LI(
                    H4(
                        A(
                            "Namespaces",
                            href="#" + namespace_id,
                        )
                    )
                )
            )

        if len(self.sections) > 0:
            legend_id = ctx.fragment(LONTOD.Legend, group="section")

            children.append(
                LI(
                    H4(
                        A(
                            "Legend",
                            href="#" + legend_id,
                        )
                    )
                )
            )

        return DIV(
            H3("Table of Contents"),
            UL(children, _class="first"),
            _class="toc",
        )
