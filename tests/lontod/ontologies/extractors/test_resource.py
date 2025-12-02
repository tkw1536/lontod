"""Test the resource extractor module."""

from pathlib import Path

import pytest
from rdflib import Graph
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, SDO, SKOS
from rdflib.term import BNode, Literal, URIRef
from syrupy.assertion import SnapshotAssertion

from lontod.ontologies.data.meta import MetaOntologies
from lontod.ontologies.extractors.meta import MetaExtractor
from lontod.ontologies.extractors.resource import ResourceExtractor
from lontod.utils.frozendict import FrozenDict
from lontod.utils.ns import BrokenSplitNamespaceManager

ASSETS_DIR = Path(__file__).parent.parent / "assets"


@pytest.fixture
def meta() -> MetaOntologies:
    """Return the meta ontologies."""
    return MetaExtractor()()


@pytest.fixture
def empty_meta() -> MetaOntologies:
    """Return empty meta ontologies."""
    return MetaOntologies(
        types=FrozenDict({}),
        titles=FrozenDict({}),
        props=FrozenDict({}),
    )


@pytest.fixture
def simple_graph() -> Graph:
    """Create a simple graph for testing."""
    g = Graph()
    g.namespace_manager = BrokenSplitNamespaceManager(g)
    g.bind("ex", "http://example.org/")
    return g


def test_instantiation(simple_graph: Graph, empty_meta: MetaOntologies) -> None:
    """Test that ResourceExtractor can be instantiated."""
    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor is not None


def test_simple_uri(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of a simple URI."""
    uri = URIRef("http://example.org/SomeClass")
    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(uri, prop=None) == snapshot


def test_uri_with_meta_title(
    simple_graph: Graph, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of URI with title from metadata."""
    uri = URIRef("http://example.org/TitledClass")
    title = Literal("Titled Class", lang="en")
    meta = MetaOntologies(
        types=FrozenDict({}),
        titles=FrozenDict({uri: (title,)}),
        props=FrozenDict({}),
    )
    extractor = ResourceExtractor(ont=simple_graph, meta=meta)
    assert extractor(uri, prop=None) == snapshot


def test_uri_with_dcterms_title(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of URI with dcterms:title in graph."""
    uri = URIRef("http://example.org/DirectTitledClass")
    title = Literal("Direct Title", lang="en")
    simple_graph.add((uri, DCTERMS.title, title))
    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(uri, prop=None) == snapshot


def test_simple_literal(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of a simple literal."""
    lit = Literal("Some text value")
    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(lit, prop=None) == snapshot


def test_example_literal(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of a skos:example literal."""
    lit = Literal("Example code")
    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(lit, prop=SKOS.example) == snapshot


def test_literal_with_uri_value(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test that literals with valid URI values are converted to ResourceReference."""
    lit = Literal("http://example.org/SomeResource")
    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(lit, prop=None) == snapshot


def test_simple_blank_node(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of a simple blank node."""
    node = BNode("fixed_id")
    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(node, prop=None) == snapshot


def test_agent_from_bnode(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of an agent from a blank node."""
    node = BNode("agent_node")
    simple_graph.add((node, RDF.type, PROV.Agent))
    simple_graph.add((node, SDO.name, Literal("John Doe")))
    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(node, prop=None) == snapshot


def test_agent_from_uri(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of an agent from a URI."""
    uri = URIRef("http://example.org/person/john")
    simple_graph.add((uri, RDF.type, PROV.Agent))
    simple_graph.add((uri, SDO.name, Literal("John Doe")))
    simple_graph.add((uri, SDO.url, URIRef("http://example.org/john")))
    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(uri, prop=None) == snapshot


def test_agent_with_affiliation(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of an agent with affiliation."""
    agent = BNode("agent")
    affiliation = BNode("affiliation")
    simple_graph.add((agent, RDF.type, PROV.Agent))
    simple_graph.add((agent, SDO.name, Literal("Jane Doe")))
    simple_graph.add((agent, SDO.affiliation, affiliation))
    simple_graph.add((affiliation, SDO.name, Literal("Example University")))
    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(agent, prop=None) == snapshot


def test_cardinality_restriction(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of a cardinality restriction."""
    restriction = BNode("restriction")
    prop_uri = URIRef("http://example.org/hasProperty")
    simple_graph.add((restriction, RDF.type, OWL.Restriction))
    simple_graph.add((restriction, OWL.onProperty, prop_uri))
    simple_graph.add((restriction, OWL.cardinality, Literal(1)))
    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(restriction, prop=None) == snapshot


def test_min_cardinality_restriction(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of a minCardinality restriction."""
    restriction = BNode("restriction")
    prop_uri = URIRef("http://example.org/hasProperty")
    simple_graph.add((restriction, RDF.type, OWL.Restriction))
    simple_graph.add((restriction, OWL.onProperty, prop_uri))
    simple_graph.add((restriction, OWL.minCardinality, Literal(0)))
    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(restriction, prop=None) == snapshot


def test_max_cardinality_restriction(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of a maxCardinality restriction."""
    restriction = BNode("restriction")
    prop_uri = URIRef("http://example.org/hasProperty")
    simple_graph.add((restriction, RDF.type, OWL.Restriction))
    simple_graph.add((restriction, OWL.onProperty, prop_uri))
    simple_graph.add((restriction, OWL.maxCardinality, Literal(5)))
    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(restriction, prop=None) == snapshot


def test_all_values_from_restriction(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of an allValuesFrom restriction."""
    restriction = BNode("restriction")
    prop_uri = URIRef("http://example.org/hasProperty")
    class_uri = URIRef("http://example.org/SomeClass")
    simple_graph.add((restriction, RDF.type, OWL.Restriction))
    simple_graph.add((restriction, OWL.onProperty, prop_uri))
    simple_graph.add((restriction, OWL.allValuesFrom, class_uri))
    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(restriction, prop=None) == snapshot


def test_some_values_from_restriction(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of a someValuesFrom restriction."""
    restriction = BNode("restriction")
    prop_uri = URIRef("http://example.org/hasProperty")
    class_uri = URIRef("http://example.org/SomeClass")
    simple_graph.add((restriction, RDF.type, OWL.Restriction))
    simple_graph.add((restriction, OWL.onProperty, prop_uri))
    simple_graph.add((restriction, OWL.someValuesFrom, class_uri))
    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(restriction, prop=None) == snapshot


def test_union_class(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of a union class."""
    node = BNode("union_class")
    list_node = BNode("list1")
    rest_node = BNode("list2")
    class1 = URIRef("http://example.org/Class1")
    class2 = URIRef("http://example.org/Class2")

    simple_graph.add((node, RDF.type, OWL.Class))
    simple_graph.add((node, OWL.unionOf, list_node))
    simple_graph.add((list_node, RDF.first, class1))
    simple_graph.add((list_node, RDF.rest, rest_node))
    simple_graph.add((rest_node, RDF.first, class2))
    simple_graph.add((rest_node, RDF.rest, RDF.nil))

    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(node, prop=None) == snapshot


def test_intersection_class(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of an intersection class."""
    node = BNode("intersection_class")
    list_node = BNode("list1")
    rest_node = BNode("list2")
    class1 = URIRef("http://example.org/ClassA")
    class2 = URIRef("http://example.org/ClassB")

    simple_graph.add((node, RDF.type, OWL.Class))
    simple_graph.add((node, OWL.intersectionOf, list_node))
    simple_graph.add((list_node, RDF.first, class1))
    simple_graph.add((list_node, RDF.rest, rest_node))
    simple_graph.add((rest_node, RDF.first, class2))
    simple_graph.add((rest_node, RDF.rest, RDF.nil))

    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(node, prop=None) == snapshot


def test_multiple_objects(
    simple_graph: Graph, empty_meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test extraction of multiple objects."""
    uri1 = URIRef("http://example.org/Class1")
    uri2 = URIRef("http://example.org/Class2")
    lit = Literal("Some value")

    extractor = ResourceExtractor(ont=simple_graph, meta=empty_meta)
    assert extractor(uri1, uri2, lit, prop=None) == snapshot


RDF_FILES = [
    "gnd_20240806.rdf",
    "met-annot.rdf",
    "met-core.rdf",
    "n4c.rdf",
]


@pytest.mark.parametrize("rdf_file", RDF_FILES)
def test_resource_extractor_on_real_data(
    rdf_file: str, meta: MetaOntologies, snapshot: SnapshotAssertion
) -> None:
    """Test ResourceExtractor on real RDF files."""
    graph = Graph()
    graph.namespace_manager = BrokenSplitNamespaceManager(graph)
    graph.parse(ASSETS_DIR / rdf_file, format="xml")
    extractor = ResourceExtractor(ont=graph, meta=meta)

    # Extract URIRef subjects only (skip BNodes for deterministic ordering)
    # Also skip URIs ending with # as they can't be split
    subjects = sorted(
        (
            s
            for s in graph.subjects()
            if isinstance(s, URIRef) and not str(s).endswith("#")
        ),
        key=str,
    )[:20]
    results = [extractor(s, prop=None) for s in subjects]

    assert results == snapshot
