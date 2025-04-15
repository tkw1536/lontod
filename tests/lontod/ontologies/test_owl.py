"""Tests the owl module"""

import json
from os.path import dirname, join
from typing import Tuple, cast

import pytest
from bs4 import BeautifulSoup

from lontod.ontologies import owl


@pytest.fixture
def html_file(request: pytest.FixtureRequest) -> BeautifulSoup:
    """loads an html fixture with the given name"""
    path = join(dirname(__file__), "fixtures", request.param)
    with open(path, "r", encoding="utf-8") as f:
        return BeautifulSoup(f, "html.parser")


@pytest.fixture
def want_definienda(request: pytest.FixtureRequest) -> list[Tuple[str, str | None]]:
    """loads a want_definienda fixture with the given name"""
    path = join(dirname(__file__), "fixtures", request.param)
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    data = cast(list[list[str | None]], raw)
    return [cast(Tuple[str, str | None], tuple(l)) for l in data]


@pytest.mark.parametrize(
    "html_file, uri, want_definienda",
    [("crm_ontology.html", "http://erlangen-crm.org/200717/", "crm_ontology.json")],
    indirect=["html_file", "want_definienda"],
)
def test_definienda_of(
    html_file: BeautifulSoup,  # pylint: disable=W0621
    uri: str,
    want_definienda: list[Tuple[str, str | None]],  # pylint: disable=W0621
) -> None:
    """tests the definienda_of method"""

    got_definienda = owl.definienda_of(
        html_file,
        uri,
    )

    assert list(got_definienda) == want_definienda
