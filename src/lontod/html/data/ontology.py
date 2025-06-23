"""Dataclasses describing the ontology itself."""

from collections.abc import Generator, Sequence
from dataclasses import dataclass
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
from rdflib.term import Literal, URIRef

from ._rdf import LONTOD, PropertyKind
from .core import HTMLable, RenderContext
from .meta import MetaProperty
from .resource import RDFResources

# TODO: ensure it's a sequence everywhere


@final
@dataclass(frozen=True)
class PropertyResourcePair:
    """a pair of information about a property and its' values."""

    prop: MetaProperty
    resources: RDFResources


@final
@dataclass(frozen=True)
class Definiendum(HTMLable):
    """something being defined in the ontology."""

    iri: URIRef
    rdf_type: PropertyKind

    titles: Sequence[Literal]

    @property
    def title(self) -> Literal | None:
        """Primary title (if any)."""
        if len(self.titles) == 0:
            return None
        return self.titles[0]

    props: Sequence[PropertyResourcePair]

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        d = div(
            h3(
                *(span(t, lang=t.language) for t in self.titles),
                sup(
                    self.rdf_type.abbrev,
                    _class=f"sup-{self.rdf_type.abbrev}",
                    title=self.rdf_type.inline_title,
                ),
            ),
            id=ctx.fragment(self.iri, self.title),
            _class="property entity",
        )

        t = table(tr(th("IRI"), td(code(str(self.iri)))))
        d.appendChild(t)

        for pair in self.props:
            t.appendChild(
                tr(th(pair.prop.to_html(ctx)), td(pair.resources.to_html(ctx)))
            )

        return d


# TODO: join with TypedDefienda


@dataclass(frozen=True)
class OntologyDefinienda(HTMLable):
    """Definienda about the ontology as a whole."""

    iri: URIRef
    titles: Sequence[Literal]

    def title(self) -> Literal | None:
        """Primary title (if any)."""
        if len(self.titles) == 0:
            return None
        return self.titles[0]

    properties: Sequence[PropertyResourcePair]

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        metadata_id = ctx.fragment(LONTOD.Metadata, group="section")
        d = div(
            h1(
                *(span(t, lang=t.language) for t in self.titles),
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

    rdf_type: PropertyKind

    definienda: Sequence[Definiendum]

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        sec = section(
            id=ctx.fragment(self.rdf_type.iri, group="section"),
            _class="section classes",
        )
        sec.appendChild(h2(self.rdf_type.plural_title))

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

    @override
    def to_html(self, ctx: RenderContext) -> document:
        doc = document(title=self.metadata.titles)

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
                            sec.rdf_type.abbrev,
                            _class="sup-" + sec.rdf_type.abbrev,
                            title=sec.rdf_type.inline_title,
                        )
                    ),
                    td(sec.rdf_type.plural_title),
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
                        sec.rdf_type.plural_title,
                        href="#" + ctx.fragment(sec.rdf_type.iri, group="section"),
                    )
                ),
                u2,
            )
            u1.appendChild(li(c))

            for definiendum in sec.definienda:
                href = "#" + ctx.fragment(definiendum.iri, definiendum.title)
                title = (
                    definiendum.title or "(No title)"
                )  # TODO: Smarter selection of title

                u2.appendChild(li(a(title, href=href)))

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
