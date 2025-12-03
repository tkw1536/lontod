"""Test the core module."""

import pytest
from rdflib.term import Literal, URIRef
from syrupy.assertion import SnapshotAssertion

from lontod.ontologies.data.core import (
    ContentRendering,
    RenderContext,
    _remove_non_ascii_chars,
)
from lontod.ontologies.data.ontology import Ontology, OntologyDefinienda
from lontod.utils.frozendict import FrozenDict


@pytest.fixture
def empty_ontology() -> Ontology:
    """Create an empty ontology for testing."""
    return Ontology(
        schema_json="{}",
        metadata=OntologyDefinienda(
            iri=URIRef("http://example.org/ontology"),
            properties=FrozenDict({}),
        ),
        sections=(),
        namespaces=FrozenDict(
            {
                "ex": URIRef("http://example.org/"),
                "other": URIRef("http://other.org/ns#"),
            }
        ),
    )


@pytest.fixture
def render_context(empty_ontology: Ontology) -> RenderContext:
    """Create a render context for testing."""
    return RenderContext(empty_ontology)


class TestContentRendering:
    """Test ContentRendering enum."""

    def test_show_as_text(self, snapshot: SnapshotAssertion) -> None:
        """Test SHOW_AS_TEXT rendering."""
        lit = Literal("Hello World", lang="en")
        result = ContentRendering.SHOW_AS_TEXT(lit)
        assert result == snapshot

    def test_show_as_text_no_lang(self, snapshot: SnapshotAssertion) -> None:
        """Test SHOW_AS_TEXT rendering without language."""
        lit = Literal("Plain text")
        result = ContentRendering.SHOW_AS_TEXT(lit)
        assert result == snapshot

    def test_show_sanitized_markdown(self, snapshot: SnapshotAssertion) -> None:
        """Test SHOW_SANITIZED_MARKDOWN rendering."""
        lit = Literal("**Bold** and *italic*", lang="en")
        result = ContentRendering.SHOW_SANITIZED_MARKDOWN(lit)
        assert result == snapshot

    def test_show_sanitized_markdown_with_script(
        self, snapshot: SnapshotAssertion
    ) -> None:
        """Test SHOW_SANITIZED_MARKDOWN strips dangerous tags."""
        lit = Literal("<script>alert('xss')</script>Safe text")
        result = ContentRendering.SHOW_SANITIZED_MARKDOWN(lit)
        assert result == snapshot

    def test_show_raw_markdown(self, snapshot: SnapshotAssertion) -> None:
        """Test SHOW_RAW_MARKDOWN rendering."""
        lit = Literal("# Heading\n\nParagraph", lang="de")
        result = ContentRendering.SHOW_RAW_MARKDOWN(lit)
        assert result == snapshot


class TestRenderContext:
    """Test RenderContext class."""

    def test_ontology_property(self, empty_ontology: Ontology) -> None:
        """Test that ontology property returns the ontology."""
        ctx = RenderContext(empty_ontology)
        assert ctx.ontology is empty_ontology

    def test_render_content(
        self, empty_ontology: Ontology, snapshot: SnapshotAssertion
    ) -> None:
        """Test render_content method."""
        ctx = RenderContext(empty_ontology)
        lit = Literal("Test content")
        assert ctx.render_content(lit) == snapshot

    def test_render_content_with_text_mode(
        self, empty_ontology: Ontology, snapshot: SnapshotAssertion
    ) -> None:
        """Test render_content with text mode."""
        ctx = RenderContext(empty_ontology, ContentRendering.SHOW_AS_TEXT)
        lit = Literal("**Not bold**")
        assert ctx.render_content(lit) == snapshot

    def test_format_iri_with_namespace(
        self, render_context: RenderContext, snapshot: SnapshotAssertion
    ) -> None:
        """Test format_iri with matching namespace."""
        iri = URIRef("http://example.org/SomeClass")
        assert render_context.format_iri(iri) == snapshot

    def test_format_iri_with_hash_namespace(
        self, render_context: RenderContext, snapshot: SnapshotAssertion
    ) -> None:
        """Test format_iri with hash namespace."""
        iri = URIRef("http://other.org/ns#Property")
        assert render_context.format_iri(iri) == snapshot

    def test_format_iri_no_namespace(
        self, render_context: RenderContext, snapshot: SnapshotAssertion
    ) -> None:
        """Test format_iri without matching namespace."""
        iri = URIRef("http://unknown.org/Thing")
        assert render_context.format_iri(iri) == snapshot

    def test_format_iri_caching(self, render_context: RenderContext) -> None:
        """Test that format_iri caches results."""
        iri = URIRef("http://example.org/CachedClass")
        result1 = render_context.format_iri(iri)
        result2 = render_context.format_iri(iri)
        assert result1 == result2

    def test_fragment_simple(
        self, render_context: RenderContext, snapshot: SnapshotAssertion
    ) -> None:
        """Test fragment generation for simple URI."""
        iri = URIRef("http://example.org/MyClass")
        assert render_context.fragment(iri) == snapshot

    def test_fragment_with_hash(
        self, render_context: RenderContext, snapshot: SnapshotAssertion
    ) -> None:
        """Test fragment generation for URI with hash."""
        iri = URIRef("http://example.org/ns#Property")
        assert render_context.fragment(iri) == snapshot

    def test_fragment_with_group(
        self, render_context: RenderContext, snapshot: SnapshotAssertion
    ) -> None:
        """Test fragment generation with group."""
        iri = URIRef("http://example.org/Section")
        assert render_context.fragment(iri, group="section") == snapshot

    def test_fragment_uniqueness(self, render_context: RenderContext) -> None:
        """Test that same IRI returns same fragment."""
        iri = URIRef("http://example.org/UniqueClass")
        frag1 = render_context.fragment(iri)
        frag2 = render_context.fragment(iri)
        assert frag1 == frag2

    def test_fragment_different_iris(self, render_context: RenderContext) -> None:
        """Test that different IRIs get different fragments."""
        iri1 = URIRef("http://example.org/Class1")
        iri2 = URIRef("http://example.org/Class2")
        frag1 = render_context.fragment(iri1)
        frag2 = render_context.fragment(iri2)
        assert frag1 != frag2

    def test_fragment_collision_handling(
        self, render_context: RenderContext, snapshot: SnapshotAssertion
    ) -> None:
        """Test fragment collision handling with suffix."""
        # Create two URIs that would have the same fragment
        iri1 = URIRef("http://example.org/ns/Thing")
        iri2 = URIRef("http://other.org/ns/Thing")
        frag1 = render_context.fragment(iri1)
        frag2 = render_context.fragment(iri2)
        assert (frag1, frag2) == snapshot

    def test_fragment_same_iri_different_groups(
        self, render_context: RenderContext, snapshot: SnapshotAssertion
    ) -> None:
        """Test same IRI in different groups."""
        iri = URIRef("http://example.org/Item")
        frag_default = render_context.fragment(iri)
        frag_section = render_context.fragment(iri, group="section")
        assert (frag_default, frag_section) == snapshot

    def test_close(self, render_context: RenderContext) -> None:
        """Test close method (currently no-op)."""
        render_context.close()  # Should not raise


class TestRemoveNonAsciiChars:
    """Test _remove_non_ascii_chars function."""

    def test_ascii_only(self, snapshot: SnapshotAssertion) -> None:
        """Test with ASCII-only string."""
        assert _remove_non_ascii_chars("Hello World") == snapshot

    def test_with_non_ascii(self, snapshot: SnapshotAssertion) -> None:
        """Test with non-ASCII characters."""
        assert _remove_non_ascii_chars("Héllo Wörld") == snapshot

    def test_with_ampersand(self, snapshot: SnapshotAssertion) -> None:
        """Test that ampersand is removed."""
        assert _remove_non_ascii_chars("A & B") == snapshot

    def test_with_unicode(self, snapshot: SnapshotAssertion) -> None:
        """Test with various unicode characters."""
        assert _remove_non_ascii_chars("Test 日本語 Text") == snapshot

    def test_empty_string(self, snapshot: SnapshotAssertion) -> None:
        """Test with empty string."""
        assert _remove_non_ascii_chars("") == snapshot

