"""Test the core extractor module."""

import pytest
from rdflib.term import URIRef

from lontod.ontologies.extractors import core


@pytest.mark.parametrize(
    ("iri", "want"),
    [
        # CamelCase with uppercase first char -> title case
        (URIRef("http://example.org/ns#PersonName"), "Person Name"),
        (URIRef("http://example.org/ns#SomeClass"), "Some Class"),
        (URIRef("http://example.org/ns#XMLParser"), "Xml Parser"),
        (URIRef("http://example.org/ns#HTTPSConnection"), "Https Connection"),
        # camelCase with lowercase first char -> lower case
        (URIRef("http://example.org/ns#personName"), "person name"),
        (URIRef("http://example.org/ns#someProperty"), "some property"),
        (URIRef("http://example.org/ns#xmlParser"), "xml parser"),
        # Single word, uppercase -> title case
        (URIRef("http://example.org/ns#Person"), "Person"),
        (URIRef("http://example.org/ns#Class"), "Class"),
        # Single word, lowercase -> lower case
        (URIRef("http://example.org/ns#person"), "person"),
        (URIRef("http://example.org/ns#property"), "property"),
        # With hash fragment
        (URIRef("http://example.org/ns#Person#fragment"), "fragment"),
        (URIRef("http://example.org/ns#person#fragment"), "fragment"),
        # Longer paths
        (URIRef("http://example.org/vocab/ns#PersonName"), "Person Name"),
        (URIRef("http://example.org/vocab/ns#personName"), "person name"),
    ],
)
def test_iri_to_title_success(iri: URIRef, want: str) -> None:
    """Test successful iri_to_title conversions."""
    assert core.iri_to_title(iri) == want


@pytest.mark.parametrize(
    "iri",
    [
        # Ending in slash
        URIRef("http://example.org/ns/"),
        URIRef("http://example.org/"),
        # Less than 4 segments (only domain)
        URIRef("http://example.org"),
        URIRef("https://example.org"),
        # Ending in hash
        URIRef("http://example.org/ns#"),
        URIRef("http://example.org/ns/Person#"),
        # Empty last segment
        URIRef("http://example.org/ns//"),
    ],
)
def test_iri_to_title_returns_none(iri: URIRef) -> None:
    """Test that iri_to_title returns None for invalid URIs."""
    assert core.iri_to_title(iri) is None
