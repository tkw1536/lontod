"""Tests the owl module."""

import json
import operator
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest
from bs4 import BeautifulSoup
from rdflib import Graph, Literal, Node
from rdflib.namespace import XSD

from lontod.ontologies import owl

FIXTURES = Path(__file__).parent / "fixtures" / "definienda_of"


@pytest.fixture
def html_file(request: pytest.FixtureRequest) -> BeautifulSoup:
    """Load an html fixture with the given name."""
    path = FIXTURES / str(request.param)
    with path.open("r", encoding="utf-8") as f:
        return BeautifulSoup(f, "html.parser")


@pytest.fixture
def want_definienda(request: pytest.FixtureRequest) -> list[tuple[str, str | None]]:
    """Load a want_definienda fixture with the given name."""
    path = FIXTURES / str(request.param)
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    data = cast("list[list[str | None]]", raw)
    return [cast("tuple[str, str | None]", tuple(case)) for case in data]


@pytest.mark.parametrize(
    ("html_file", "want_definienda"),
    [("crm_ontology.html", "crm_ontology.json")],
    indirect=["html_file", "want_definienda"],
)
def test_definienda_of(
    html_file: BeautifulSoup,  # pylint: disable=W0621
    want_definienda: list[tuple[str, str | None]],  # pylint: disable=W0621
) -> None:
    """Tests the definienda_of method."""
    got = owl.definienda_of(
        html_file,
    )

    norm_got = sorted(got, key=operator.itemgetter(0))
    norm_want = sorted(want_definienda, key=operator.itemgetter(0))

    assert list(norm_got) == list(norm_want)


def _load_graph(*paths: str) -> Graph:
    """Load a graph from a specific path."""
    path = FIXTURES.parent
    for p in paths:
        path /= p
    g = Graph()
    g.parse(path.read_bytes())
    return g


@pytest.fixture
def graph(request: pytest.FixtureRequest) -> Graph:
    """Load a graph fixture."""
    return _load_graph("insert_fallback_title", request.param)


@pytest.fixture
def want_graph(request: pytest.FixtureRequest) -> Graph:
    """Load a want_graph fixture."""
    return _load_graph("insert_fallback_title", request.param)


@pytest.mark.parametrize(
    ("graph", "titles", "want_graph", "want_ok"),
    [
        (
            "with_title.nt",
            (Literal("", datatype=XSD.string),),
            "with_title.nt",
            False,
        ),
        (
            "without_title.nt",
            (Literal("", datatype=XSD.string),),
            "without_title_added.nt",
            True,
        ),
    ],
    indirect=["graph", "want_graph"],
)
def test_insert_fallback_title(
    graph: Graph,  # pylint: disable=W0621
    titles: Sequence[Node],
    want_graph: Graph,  # pylint: disable=W0621
    want_ok: bool,
) -> None:
    """Tests the insert_fallback_title function."""
    # clone the graph for testing
    clone = Graph()
    for g in graph:
        clone.add(g)

    got_ok = owl.insert_fallback_title(clone, *titles)
    assert got_ok == want_ok
    assert set(clone) == set(want_graph)
