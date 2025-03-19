"""Test the graph module"""

from typing import Optional, Sequence

import pytest
from rdflib import Graph, Literal
from rdflib.graph import _TripleType
from rdflib.namespace import XSD, Namespace

from lontod.utils import graph

EX = Namespace("http://example.com/namespace")


@pytest.mark.parametrize(
    "edges, want",
    [
        (
            [
                (EX.subject_1, EX.predicate, EX.object),
            ],
            [
                (EX.subject_1, EX.predicate, EX.object),
            ],
        ),
        (
            [
                (EX.subject_1, EX.predicate, Literal("hello world")),
                (EX.subject_1, EX.predicate, Literal("<b>safe html</b>")),
                (
                    EX.subject_1,
                    EX.predicate,
                    Literal("some text with \t      weird spaces\t"),
                ),
                (
                    EX.subject_1,
                    EX.predicate,
                    Literal("unsafe html 1<script>alert('unsafe');</script>"),
                ),
            ],
            [
                (EX.subject_1, EX.predicate, Literal("hello world")),
                (EX.subject_1, EX.predicate, Literal("<b>safe html</b>")),
                (
                    EX.subject_1,
                    EX.predicate,
                    Literal("some text with \t      weird spaces\t"),
                ),
                (EX.subject_1, EX.predicate, Literal("unsafe html 1")),
            ],
        ),
        (
            [
                (EX.subject_1, EX.predicate, Literal("hello world", lang="en")),
                (EX.subject_1, EX.predicate, Literal("<b>safe html</b>", lang="en")),
                (
                    EX.subject_1,
                    EX.predicate,
                    Literal("some text with \t      weird spaces\t", lang="en"),
                ),
                (
                    EX.subject_1,
                    EX.predicate,
                    Literal(
                        "unsafe html 2<script>alert('unsafe');</script>", lang="en"
                    ),
                ),
            ],
            [
                (EX.subject_1, EX.predicate, Literal("hello world", lang="en")),
                (EX.subject_1, EX.predicate, Literal("<b>safe html</b>", lang="en")),
                (
                    EX.subject_1,
                    EX.predicate,
                    Literal("some text with \t      weird spaces\t", lang="en"),
                ),
                (EX.subject_1, EX.predicate, Literal("unsafe html 2", lang="en")),
            ],
        ),
        (
            [
                (
                    EX.subject_1,
                    EX.predicate,
                    Literal("hello world", datatype=XSD.string),
                ),
                (
                    EX.subject_1,
                    EX.predicate,
                    Literal("<b>safe html</b>", datatype=XSD.string),
                ),
                (
                    EX.subject_1,
                    EX.predicate,
                    Literal(
                        "some text with \t      weird spaces\t", datatype=XSD.string
                    ),
                ),
                (
                    EX.subject_1,
                    EX.predicate,
                    Literal(
                        "unsafe html 3<script>alert('unsafe');</script>",
                        datatype=XSD.string,
                    ),
                ),
            ],
            [
                (
                    EX.subject_1,
                    EX.predicate,
                    Literal("hello world", datatype=XSD.string),
                ),
                (
                    EX.subject_1,
                    EX.predicate,
                    Literal("<b>safe html</b>", datatype=XSD.string),
                ),
                (
                    EX.subject_1,
                    EX.predicate,
                    Literal(
                        "some text with \t      weird spaces\t", datatype=XSD.string
                    ),
                ),
                (
                    EX.subject_1,
                    EX.predicate,
                    Literal("unsafe html 3", datatype=XSD.string),
                ),
            ],
        ),
    ],
)
def test_sanitize(edges: Sequence[_TripleType], want: Sequence[_TripleType]) -> None:
    """Test the sanitize function"""

    # create the graph graph
    g = Graph()
    for e in edges:
        g.add(e)

    # sanitize it
    graph.sanitize(g)
    assert_graph(g, want)


@pytest.mark.parametrize(
    "edges, langs, want",
    [
        (
            [
                (EX.subject_1, EX.predicate, Literal("no language")),
                (EX.subject_2, EX.predicate, Literal("german", lang="de")),
                (EX.subject_2, EX.predicate, Literal("english", lang="en")),
                (EX.subject_3, EX.predicate, Literal("english", lang="en")),
                (EX.subject_3, EX.predicate, Literal("french", lang="fr")),
            ],
            None,
            [
                (EX.subject_1, EX.predicate, Literal("no language")),
                (EX.subject_2, EX.predicate, Literal("german", lang="de")),
                (EX.subject_3, EX.predicate, Literal("english", lang="en")),
            ],
        ),
        (
            [
                (EX.subject_1, EX.predicate, Literal("no language")),
                (EX.subject_2, EX.predicate, Literal("german", lang="de")),
                (EX.subject_2, EX.predicate, Literal("english", lang="en")),
                (EX.subject_3, EX.predicate, Literal("english", lang="en")),
                (EX.subject_3, EX.predicate, Literal("french", lang="fr")),
                (EX.subject_4, EX.predicate, Literal("german", lang="de")),
            ],
            ["fr", "en"],
            [
                (EX.subject_1, EX.predicate, Literal("no language")),
                (EX.subject_2, EX.predicate, Literal("english", lang="en")),
                (EX.subject_3, EX.predicate, Literal("french", lang="fr")),
                (EX.subject_4, EX.predicate, Literal("german", lang="de")),
            ],
        ),
    ],
)
def test_restrict_languages(
    edges: Sequence[_TripleType],
    langs: Optional[Sequence[str]],
    want: Sequence[_TripleType],
) -> None:
    """Test the sanitize function"""

    # create the graph graph
    g = Graph()
    for e in edges:
        g.add(e)

    # do the restriction
    graph.restrict_languages(g, langs)
    assert_graph(g, want)


def assert_graph(g: Graph, edges: Sequence[_TripleType]) -> None:
    """Asserts that a graph only contains the given edges"""

    try:
        assert len(edges) == len(g)

        for edge in edges:
            assert edge in g
    except AssertionError:
        print("graph contains edges:")
        for edge in g:
            print(edge)
        raise
