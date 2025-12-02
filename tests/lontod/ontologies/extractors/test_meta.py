"""Test the meta extractor module."""

from syrupy.assertion import SnapshotAssertion

from lontod.ontologies.extractors.meta import MetaExtractor


def test_meta_extractor_instantiation() -> None:
    """Test that MetaExtractor can be instantiated."""
    extractor = MetaExtractor()
    assert extractor is not None


def test_meta_extractor_call(snapshot: SnapshotAssertion) -> None:
    """Test that MetaExtractor returns MetaOntologies when called."""
    extractor = MetaExtractor()
    result = extractor()
    assert result == snapshot
