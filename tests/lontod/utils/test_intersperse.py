"""test the intersperse module."""

from collections.abc import Iterable, Iterator

import pytest

from lontod.utils import intersperse


@pytest.mark.parametrize(
    ("it", "sep", "want"),
    [
        ((), "a", ()),
        (("1",), "a", ("1",)),
        (("1", "2"), "b", ("1", "b", "2")),
        (("1", "2", "3"), "c", ("1", "c", "2", "c", "3")),
    ],
)
def test_intersperse(it: Iterator[str], sep: str, want: Iterable[str]) -> None:
    """Test the as_utf8 function."""
    got = intersperse.intersperse(it, sep)
    assert list(got) == list(want)
