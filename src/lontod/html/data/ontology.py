"""Dataclasses describing the ontology itself."""

from collections.abc import Generator, Sequence
from dataclasses import dataclass
from importlib import resources
from itertools import chain
from typing import override

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

from ._rdf import PropertyKind
from .core import HTMLable, RenderContext
from .meta import MetaProperty
from .resource import RDFResources

# TODO: make everything final
# TODO: ensure it's a sequence everywhere


@dataclass
class PropertyResourcePair:
    """a pair of information about a property and its' values."""

    prop: MetaProperty
    resources: RDFResources


@dataclass
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
        info = self.rdf_type.info

        d = div(
            h3(
                *(span(t, lang=t.language) for t in self.titles),
                sup(
                    info.abbrev,
                    _class=f"sup-{info.abbrev}",
                    title=info.inline_title,
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


@dataclass
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
        d = div(
            h1(
                *(span(t, lang=t.language) for t in self.titles),
            ),
            id="metadata",
            _class="section",
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


@dataclass
class TypeDefinienda(HTMLable):
    """Definienda of a specific type."""

    rdf_type: PropertyKind

    definienda: Sequence[Definiendum]

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        info = self.rdf_type.info

        sec = section(id=info.toc_id, _class="section")
        sec.appendChild(h2(info.plural_title))
        for defienendum in self.definienda:
            sec.appendChild(defienendum.to_html(ctx))
        return sec


@dataclass
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
            [self._make_namespaces()],
            [self._make_legend()],
            [self._make_toc(ctx)],
        ):
            content.appendChild(tag)

        return content

    def _make_legend(
        self,
    ) -> html_tag:
        legend = div(id="legend")

        h = h2("Legend")
        legend.appendChild(h)

        t = table(_class="entity")
        legend.appendChild(t)

        for sec in self.sections:
            if len(sec.definienda) == 0:
                continue

            info = sec.rdf_type.info

            t.appendChild(
                tr(
                    td(
                        sup(
                            info.abbrev,
                            _class="sup-" + info.abbrev,
                            title=info.inline_title,
                        )
                    ),
                    td(info.plural_title),
                )
            )
        return legend

    def _make_namespaces(self) -> html_tag:
        namespaces = div(id="namespaces")
        with namespaces:
            h2("Namespaces")
            with dl():
                for prefix, ns in self.namespaces:
                    p_ = prefix if prefix != "" else ":"
                    dt(p_, id=p_)
                    dd(code(ns))
        return namespaces

    def _make_toc(self, ctx: RenderContext) -> html_tag:
        d = div(h3("Table of Contents"), id="toc")

        u1 = ul(_class="first")
        d.appendChild(u1)

        for sec in self.sections:
            if len(sec.definienda) == 0:
                continue

            info = sec.rdf_type.info

            u2 = ul(_class="second")
            c = container(
                h4(a(info.plural_title, href="#" + info.toc_id)),
                u2,
            )
            u1.appendChild(li(c))

            for defi in sec.definienda:
                href = "#" + ctx.fragment(defi.iri, defi.title)
                title = defi.title or "(No title)"  # TODO: Smarter selection of title

                u2.appendChild(li(a(title, href=href)))

        return d
