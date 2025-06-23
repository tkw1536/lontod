"""Dataclasses describing the ontology itself."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import override

from dominate.tags import (
    code,
    dd,
    div,
    dl,
    dt,
    h1,
    h2,
    h3,
    html_tag,
    section,
    span,
    strong,
    sup,
    table,
    td,
    th,
    tr,
)
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


@dataclass
class OntologyDefinienda(HTMLable):
    """Definienda about the ontology as a whole."""

    iri: URIRef
    titles: Sequence[Literal]
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

    def toc_entries(self, ctx: RenderContext) -> tuple[str, list[tuple[str, str]]]:
        """Entries in a table of contents for this section."""
        return (
            self.rdf_type.info.toc_id,
            [
                ("#" + ctx.fragment(defi.iri, defi.title), defi.title or "(No title)")
                for defi in self.definienda
            ],
        )

    @override
    def to_html(self, ctx: RenderContext) -> html_tag:
        info = self.rdf_type.info

        sec = section(id=info.toc_id, _class="section")
        sec.appendChild(h2(info.plural_title))
        for defienendum in self.definienda:
            sec.appendChild(defienendum.to_html(ctx))
        return sec
