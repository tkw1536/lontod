"""Tests the graph module."""

import pytest
from rdflib import Graph
from rdflib.term import URIRef
from syrupy.assertion import SnapshotAssertion

from lontod.utils import graph

EXAMPLE_GRAPH = """
@prefix ex: <http://example.org/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:alice a foaf:Person ;
    foaf:name "Alice" ;
    foaf:mbox <mailto:alice@example.org> ;
    foaf:knows ex:bob .

ex:bob a foaf:Person ;
    foaf:name "Bob" ;
    foaf:mbox <mailto:bob@example.org> ;
    ex:age "30"^^xsd:integer .

ex:icecream a ex:Thing ;
    foaf:name "Ice Cream" .

ex:alice ex:likes ex:icecream .
"""


def _example_graph() -> Graph:
    g = Graph()
    g.parse(data=EXAMPLE_GRAPH, format="ttl")
    return g


@pytest.mark.parametrize(
    ("g", "always"),
    [
        (Graph(), None),
        (
            _example_graph(),
            None,
        ),
        (
            _example_graph(),
            {URIRef("http://www.w3.org/2001/XMLSchema#")},
        ),
    ],
)
def test_namespaces(
    g: Graph, always: set[URIRef] | None, snapshot: SnapshotAssertion
) -> None:
    """Test the used_namespaces function."""
    got = graph.used_namespaces(g, always=always)
    assert sorted(dict(got)) == snapshot
