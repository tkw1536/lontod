"""test the partition module."""

from collections.abc import Callable, Iterable

import pytest

from lontod.utils import partition


@pytest.mark.parametrize(
    ("it", "part", "want"),
    [
        (
            ["a", "b", "c"],
            lambda x: x,
            [
                ("a", ("a",)),
                ("b", ("b",)),
                ("c", ("c",)),
            ],
        ),
        (
            ["aa", "ba", "ab"],
            lambda x: x[0],
            [
                ("a", ("aa", "ab")),
                ("b", ("ba",)),
            ],
        ),
    ],
)
def test_partition(
    it: list[str],
    part: Callable[[str], str],
    want: Iterable[tuple[str, tuple[str, ...]]],
) -> None:
    """Test the partition function."""
    got = partition.partition(it, part)
    assert list(got) == list(want)
