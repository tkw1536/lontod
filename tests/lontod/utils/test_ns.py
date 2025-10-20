"""Test the ns module."""

import pytest
from rdflib import Graph, URIRef

from lontod.utils.ns import BrokenSplitNamespaceManager


class TestBrokenSplitNamespaceManager:
    """Test the BrokenSplitNamespaceManager class."""

    def test_compute_qname_without_trailing_slash(self) -> None:
        """Test compute_qname works normally for URIs without trailing slash."""
        graph = Graph()
        graph.bind("ex", "http://example.org/")
        manager = BrokenSplitNamespaceManager(graph)

        prefix, namespace, local_name = manager.compute_qname("http://example.org/test")
        assert prefix == "ex"
        assert namespace == URIRef("http://example.org/")
        assert local_name == "test"

    def test_compute_qname_with_trailing_slash(self) -> None:
        """Test compute_qname handles URIs with trailing slash by stripping it."""
        graph = Graph()
        graph.bind("ex", "http://example.org/")
        manager = BrokenSplitNamespaceManager(graph)

        # Test URI with trailing slash - should strip it and work
        prefix, namespace, local_name = manager.compute_qname("http://example.org/test/")
        assert prefix == "ex"
        assert namespace == URIRef("http://example.org/")
        assert local_name == "test"

    def test_compute_qname_strict_without_trailing_slash(self) -> None:
        """Test compute_qname_strict works normally for URIs without trailing slash."""
        graph = Graph()
        graph.bind("ex", "http://example.org/")
        manager = BrokenSplitNamespaceManager(graph)

        # Test normal URI without trailing slash
        prefix, namespace, local_name = manager.compute_qname_strict(
            "http://example.org/test"
        )
        assert prefix == "ex"
        assert namespace == URIRef("http://example.org/")
        assert local_name == "test"

    def test_compute_qname_strict_with_trailing_slash(self) -> None:
        """Test compute_qname_strict handles URIs with trailing slash by stripping it."""
        graph = Graph()
        graph.bind("ex", "http://example.org/")
        manager = BrokenSplitNamespaceManager(graph)

        # Test URI with trailing slash - should strip it and work
        prefix, namespace, local_name = manager.compute_qname_strict(
            "http://example.org/test/"
        )
        assert prefix == "ex"
        assert namespace == URIRef("http://example.org/")
        assert local_name == "test"

    def test_normalize_uri_without_trailing_slash(self) -> None:
        """Test normalizeUri works normally for URIs without trailing slash."""
        graph = Graph()
        graph.bind("ex", "http://example.org/")
        manager = BrokenSplitNamespaceManager(graph)

        result = manager.normalizeUri("http://example.org/test")
        assert result == "ex:test"

    def test_normalize_uri_with_trailing_slash(self) -> None:
        """Test normalizeUri handles URIs with trailing slash by stripping it."""
        graph = Graph()
        manager = BrokenSplitNamespaceManager(graph)

        # Add a namespace binding
        graph.bind("ex", "http://example.org/")

        # Test URI with trailing slash - should strip it and work
        result = manager.normalizeUri("http://example.org/test/")
        assert result == "<http://example.org/test/>"

    def test_compute_qname_error_not_trailing_slash(self) -> None:
        """Test that compute_qname raises ValueError for non-trailing-slash errors."""
        graph = Graph()
        manager = BrokenSplitNamespaceManager(graph)

        # Test with URI that doesn't end with slash but still causes error
        prefix, namespace, local_name = manager.compute_qname(
            "http://unknown-namespace.org/test"
        )
        assert prefix == "ns1"
        assert namespace == URIRef("http://unknown-namespace.org/")
        assert local_name == "test"

    def test_compute_qname_strict_error_not_trailing_slash(self) -> None:
        """Test that compute_qname_strict raises ValueError for non-trailing-slash errors."""
        graph = Graph()
        manager = BrokenSplitNamespaceManager(graph)

        # Test with URI that doesn't end with slash but still causes error
        prefix, namespace, local_name = manager.compute_qname_strict(
            "http://unknown-namespace.org/test"
        )
        assert prefix == "ns1"
        assert namespace == URIRef("http://unknown-namespace.org/")
        assert local_name == "test"

    def test_normalize_uri_error_not_trailing_slash(self) -> None:
        """Test that normalizeUri raises ValueError for non-trailing-slash errors."""
        graph = Graph()
        manager = BrokenSplitNamespaceManager(graph)

        result = manager.normalizeUri("http://unknown-namespace.org/test")
        assert result == "<http://unknown-namespace.org/test>"

    def test_empty_string_after_stripping(self) -> None:
        """Test behavior when stripping trailing slash results in empty string."""
        graph = Graph()
        manager = BrokenSplitNamespaceManager(graph)

        # Add a namespace binding
        graph.bind("ex", "http://example.org/")

        # Test URI that is just the namespace with trailing slash
        prefix, namespace, local_name = manager.compute_qname("http://example.org/")
        assert prefix == "ex"
        assert namespace == URIRef("http://example.org/")
        assert local_name == ""

    def test_generate_false_parameter(self) -> None:
        """Test that the generate parameter is passed through correctly."""
        graph = Graph()
        manager = BrokenSplitNamespaceManager(graph)

        # Test with generate=False
        with pytest.raises(KeyError):
            manager.compute_qname("http://example.org/test/", generate=False)
