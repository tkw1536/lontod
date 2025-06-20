"""Tests the owl module"""

import json
from os.path import dirname, join
from typing import Sequence, Tuple, cast

import pytest
from bs4 import BeautifulSoup
from rdflib import Graph, Literal, Node
from rdflib.namespace import XSD

from lontod.ontologies import owl


@pytest.fixture
def html_file(request: pytest.FixtureRequest) -> BeautifulSoup:
    """loads an html fixture with the given name"""
    path = join(dirname(__file__), "fixtures", "definienda_of", request.param)
    with open(path, "r", encoding="utf-8") as f:
        return BeautifulSoup(f, "html.parser")


@pytest.fixture
def want_definienda(request: pytest.FixtureRequest) -> list[Tuple[str, str | None]]:
    """loads a want_definienda fixture with the given name"""
    path = join(dirname(__file__), "fixtures", "definienda_of", request.param)
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    data = cast(list[list[str | None]], raw)
    return [cast(Tuple[str, str | None], tuple(case)) for case in data]


@pytest.mark.parametrize(
    "html_file, want_definienda",
    [("crm_ontology.html", "crm_ontology.json")],
    indirect=["html_file", "want_definienda"],
)
def test_definienda_of(
    html_file: BeautifulSoup,  # pylint: disable=W0621
    want_definienda: list[Tuple[str, str | None]],  # pylint: disable=W0621
) -> None:
    """tests the definienda_of method"""

    got = owl.definienda_of(
        html_file,
    )

    norm_got = sorted(list(got), key=lambda x: x[0])
    norm_want = sorted(list(want_definienda), key=lambda x: x[0])

    assert list(norm_got) == list(norm_want)


def _load_graph(*paths: str) -> Graph:
    """loads a graph from a specific path"""
    path = join(dirname(__file__), "fixtures", *paths)
    g = Graph()
    g.parse(path)
    return g


@pytest.fixture
def graph(request: pytest.FixtureRequest) -> Graph:
    """loads a graph fixture"""
    return _load_graph("insert_fallback_title", request.param)


@pytest.fixture
def want_graph(request: pytest.FixtureRequest) -> Graph:
    """loads a want_graph fixture"""
    return _load_graph("insert_fallback_title", request.param)


@pytest.mark.parametrize(
    "graph, titles, want_graph, want_ok",
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
    """Tests the insert_fallback_title function"""

    # clone the graph for testing
    clone = Graph()
    for g in graph:
        clone.add(g)

    got_ok = owl.insert_fallback_title(clone, *titles)
    assert got_ok == want_ok
    assert set(clone) == set(want_graph)
