"""Tests the frozendict module."""

from typing import Any

import pytest

from lontod.utils.frozendict import FrozenDict


@pytest.mark.parametrize(
    "md",
    [
        {},
        {"hello": "world"},
        {"a": 1, "b": 2},
        {1.0: "a", 2.0: "b"},
    ],
)
def test_frozen_dict_behavior(md: dict[Any, Any]) -> None:
    """Tests behavior of a frozen dict."""
    fd = FrozenDict(md)

    assert fd is not md

    # check that keys are identical
    assert tuple(fd.keys()) == tuple(md.keys())

    # check that items are identical
    assert tuple(fd.items()) == tuple(md.items())

    # check that len is identical
    assert len(fd) == len(md)

    # check that the values are identical
    for key, value in md.items():
        assert fd[key] == value


def test_frozen_dict_equality() -> None:
    """Tests equality of the frozen dict class."""
    # FrozenDicts are expected to be ==-equal within a group
    # and different between groups.
    groups: list[list[FrozenDict[Any, Any]]] = [
        [
            FrozenDict(hello="world", bye="universe"),
            FrozenDict(hello="world", bye="universe"),
            FrozenDict(bye="universe", hello="world"),
        ],
        [FrozenDict(other="world")],
        [FrozenDict(other=12)],
    ]

    for group_index, group in enumerate(groups):
        for elem_index, elem in enumerate(group):
            for inner_group_index, inner_group in enumerate(groups):
                for inner_elem_index, inner_elem in enumerate(inner_group):
                    # they are ==-equal iff they are in the same group
                    assert (elem == inner_elem) == (inner_group_index == group_index)
                    # they are is-equal iff they are in the same group and have the same index
                    assert (elem is inner_elem) == (
                        inner_group_index == group_index
                        and inner_elem_index == elem_index
                    )


@pytest.mark.parametrize(
    ("fd", "want"),
    [
        (FrozenDict(), "FrozenDict({})"),
        (FrozenDict({"hello": "world"}), "FrozenDict({'hello': 'world'})"),
        (FrozenDict({"a": 1, "b": 2}), "FrozenDict({'a': 1, 'b': 2})"),
        (FrozenDict({"b": 2, "a": 1}), "FrozenDict({'a': 1, 'b': 2})"),
        (FrozenDict({"z": 3, "a": 1, "m": 2}), "FrozenDict({'a': 1, 'm': 2, 'z': 3})"),
        (FrozenDict({"key": None}), "FrozenDict({'key': None})"),
        (FrozenDict({"x": True, "y": False}), "FrozenDict({'x': True, 'y': False})"),
        (FrozenDict({1: "a", 2: "b"}), "FrozenDict({1: 'a', 2: 'b'})"),
    ],
)
def test_frozen_dict_repr(fd: FrozenDict[Any, Any], want: str) -> None:
    """Test the repr of a FrozenDict."""
    assert repr(fd) == want
