"""Test the ontology extractor module."""

from pathlib import Path

import pytest
from rdflib import Graph
from syrupy.assertion import SnapshotAssertion

from lontod.ontologies.extractors.ontology import OntologyExtractor
from lontod.utils.ns import BrokenSplitNamespaceManager

ASSETS_DIR = Path(__file__).parent.parent / "assets"

RDF_FILES = [
    "gnd_20240806.rdf",
    "met-annot.rdf",
    "met-core.rdf",
    "n4c.rdf",
]


@pytest.mark.parametrize("rdf_file", RDF_FILES)
def test_ontology_extractor_call(rdf_file: str, snapshot: SnapshotAssertion) -> None:
    """Test that OntologyExtractor returns Ontology when called."""
    graph = Graph()
    graph.namespace_manager = BrokenSplitNamespaceManager(graph)
    graph.parse(ASSETS_DIR / rdf_file, format="xml")
    extractor = OntologyExtractor(graph)
    result = extractor()
    assert result == snapshot
