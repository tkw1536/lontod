"""Dataclasses describing the ontology itself."""

from abc import ABC
from collections import defaultdict
from collections.abc import Generator, Sequence
from dataclasses import dataclass
from functools import cached_property
from importlib import resources
from itertools import chain
from typing import final, override

from dominate.document import document
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
    section,
    span,
    strong,
    style,
    sup,
    table,
    td,
    th,
    tr,
    ul,
)
from dominate.util import container, raw
from rdflib.namespace import XSD
from rdflib.term import Literal, URIRef

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
    titles: Sequence[Literal]

    properties: Sequence[PropertyResourcePair]

    def title(self, ctx: RenderContext) -> Literal:
        """Primary titles of this definiendum used for the given context."""
        # no title available
        if len(self.titles) == 0:
            # TODO: Use the old iri_from_title here?
            return Literal(str(self.iri), datatype=XSD.anyURI)

        # group by languages, but keep relative order.
        titles_sorted = sorted(self.titles, key=lambda lit: lit.language or "")

        # find the language with the smallest preference.
        return min(titles_sorted, key=lambda lit: ctx.language_preference(lit.language))


@final
@dataclass(frozen=True)
class Definiendum(_DefiniendumLike, HTMLable):
    """something being defined in the ontology."""

    prop: IndexedProperty

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        title = self.title(ctx)
        d = div(
            h3(
                span(str(title.value), lang=title.language),
                sup(
                    self.prop.abbrev,
                    _class=f"sup-{self.prop.abbrev}",
                    title=self.prop.inline_title,
                ),
            ),
            id=ctx.fragment(self.iri, self.title(ctx)),
            _class="property entity",
        )

        t = table(tr(th("IRI"), td(code(str(self.iri)))))
        d.appendChild(t)

        for pair in self.properties:
            t.appendChild(
                tr(th(pair.prop.to_html(ctx)), td(pair.resources.to_html(ctx)))
            )

        return d


@dataclass(frozen=True)
class OntologyDefinienda(_DefiniendumLike, HTMLable):
    """Definienda about the ontology as a whole."""

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        metadata_id = ctx.fragment(LONTOD.Metadata, group="section")
        title = self.title(ctx)

        d = div(
            h1(
                span(str(title.value), lang=title.language),
            ),
            id=metadata_id,
            _class="section metadata",
        )

        d.appendChild(h2("Metadata"))

        defs = dl(div(dt(strong("IRI")), dd(code(str(self.iri)))))
        d.appendChild(defs)

        for pair in self.properties:
            defs.appendChild(
                div(
                    dt(pair.prop.to_html(ctx)),
                    dd(pair.resources.to_html(ctx)),
                )
            )

        return d


@dataclass(frozen=True)
class TypeDefinienda(HTMLable):
    """Definienda of a specific type."""

    prop: IndexedProperty
    definienda: Sequence[Definiendum]

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        sec = section(
            id=ctx.fragment(self.prop.iri, group="section"),
            _class="section classes",
        )
        sec.appendChild(h2(self.prop.plural_title))

        for definiendum in self.definienda:
            sec.appendChild(definiendum.to_html(ctx))

        return sec


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
    def to_html(self, ctx: RenderContext) -> document:
        doc = document(title=self.metadata.title(ctx))

        with doc.head:
            for tag in self._head():
                tag.render()

        body = self._make_body(ctx)
        doc.appendChild(body)

        return doc

    def _head(
        self,
    ) -> Generator[html_tag]:
        """Make <head>???</head> content."""
        css = resources.files(__package__).joinpath("assets", "style.css").read_text()
        yield style(raw("\n" + css + "\n\t"))

        yield meta(http_equiv="Content-Type", content="text/html; charset=utf-8")

        yield script(
            raw("\n" + self.schema_json + "\n\t"),
            type="application/ld+json",
            id="schema.org",
        )

    def _make_body(self, ctx: RenderContext) -> html_tag:
        content = div(id="content")
        for tag in chain(
            [self.metadata.to_html(ctx)],
            [s.to_html(ctx) for s in self.sections],
            [self._make_namespaces(ctx)],
            [self._make_legend(ctx)],
            [self._make_toc(ctx)],
        ):
            content.appendChild(tag)

        return content

    def _make_legend(self, ctx: RenderContext) -> html_tag:
        if len(self.sections) == 0:
            return container()

        legend_id = ctx.fragment(LONTOD.Legend, group="section")

        legend = div(_class="legend")

        h = h2("Legend", id=legend_id)
        legend.appendChild(h)

        t = table(_class="entity")
        legend.appendChild(t)

        for sec in self.sections:
            if len(sec.definienda) == 0:
                continue

            t.appendChild(
                tr(
                    td(
                        sup(
                            sec.prop.abbrev,
                            _class="sup-" + sec.prop.abbrev,
                            title=sec.prop.inline_title,
                        )
                    ),
                    td(sec.prop.plural_title),
                )
            )
        return legend

    def _make_namespaces(self, ctx: RenderContext) -> html_tag:
        if len(self.namespaces) == 0:
            return container()

        namespace_id = ctx.fragment(LONTOD.Namespaces, group="section")

        namespaces = div(id=namespace_id)
        with namespaces:
            h2("Namespaces")
            with dl():
                for prefix, ns in self.namespaces:
                    p_ = prefix if prefix != "" else ":"
                    dt(p_, id=p_)
                    dd(code(ns))
        return namespaces

    def _make_toc(self, ctx: RenderContext) -> html_tag:
        d = div(h3("Table of Contents"), _class="toc")

        u1 = ul(_class="first")
        d.appendChild(u1)

        metadata_id = ctx.fragment(LONTOD.Metadata, group="section")
        u1.appendChild(
            li(
                h4(
                    a(
                        "Metadata",
                        href="#" + metadata_id,
                    )
                )
            )
        )

        for sec in self.sections:
            if len(sec.definienda) == 0:
                continue

            u2 = ul(_class="second")
            c = container(
                h4(
                    a(
                        sec.prop.plural_title,
                        href="#" + ctx.fragment(sec.prop.iri, group="section"),
                    )
                ),
                u2,
            )
            u1.appendChild(li(c))

            for definiendum in sec.definienda:
                title = definiendum.title(ctx)
                href = "#" + ctx.fragment(definiendum.iri, title)
                u2.appendChild(li(a(str(title.value), href=href)))

        if len(self.namespaces) > 0:
            namespace_id = ctx.fragment(LONTOD.Namespaces, group="section")
            u1.appendChild(
                li(
                    h4(
                        a(
                            "Namespaces",
                            href="#" + namespace_id,
                        )
                    )
                )
            )

        if len(self.sections) > 0:
            legend_id = ctx.fragment(LONTOD.Legend, group="section")

            u1.appendChild(
                li(
                    h4(
                        a(
                            "Legend",
                            href="#" + legend_id,
                        )
                    )
                )
            )

        return d
