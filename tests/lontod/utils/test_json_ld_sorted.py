"""Test the json_ld_sorted module."""

from typing import Any

from lontod.utils.json_ld_sorted import sort_jsonld_by_id


def test_sort_jsonld_by_id_simple_dict() -> None:
    """Test sorting a simple dict."""
    obj = {"@id": "http://example.org/z", "name": "Z"}
    result = sort_jsonld_by_id(obj)
    assert result == {"@id": "http://example.org/z", "name": "Z"}


def test_sort_jsonld_by_id_list_of_nodes() -> None:
    """Test sorting a list of JSON-LD nodes by @id."""
    obj = [
        {"@id": "http://example.org/z", "name": "Z"},
        {"@id": "http://example.org/a", "name": "A"},
        {"@id": "http://example.org/m", "name": "M"},
    ]
    result = sort_jsonld_by_id(obj)
    assert result == [
        {"@id": "http://example.org/a", "name": "A"},
        {"@id": "http://example.org/m", "name": "M"},
        {"@id": "http://example.org/z", "name": "Z"},
    ]


def test_sort_jsonld_by_id_preserves_list_order() -> None:
    """Test that @list containers preserve order."""
    obj = {
        "@list": [
            {"@id": "http://example.org/z", "name": "Z"},
            {"@id": "http://example.org/a", "name": "A"},
            {"@id": "http://example.org/m", "name": "M"},
        ]
    }
    result = sort_jsonld_by_id(obj)
    # Order should be preserved for @list
    assert result["@list"] == [
        {"@id": "http://example.org/z", "name": "Z"},
        {"@id": "http://example.org/a", "name": "A"},
        {"@id": "http://example.org/m", "name": "M"},
    ]


def test_sort_jsonld_by_id_nested_structure() -> None:
    """Test sorting nested structures."""
    obj = {
        "@context": {"ex": "http://example.org/"},
        "@graph": [
            {"@id": "http://example.org/z", "name": "Z"},
            {"@id": "http://example.org/a", "name": "A"},
        ],
        "items": [
            {"@id": "http://example.org/m", "name": "M"},
            {"@id": "http://example.org/b", "name": "B"},
        ],
    }
    result = sort_jsonld_by_id(obj)
    assert result["@graph"] == [
        {"@id": "http://example.org/a", "name": "A"},
        {"@id": "http://example.org/z", "name": "Z"},
    ]
    assert result["items"] == [
        {"@id": "http://example.org/b", "name": "B"},
        {"@id": "http://example.org/m", "name": "M"},
    ]


def test_sort_jsonld_by_id_empty_list() -> None:
    """Test sorting an empty list."""
    obj: list[Any] = []
    result = sort_jsonld_by_id(obj)
    assert result == []


def test_sort_jsonld_by_id_list_without_ids() -> None:
    """Test that lists without @id are not sorted."""
    obj = ["a", "b", "c"]
    result = sort_jsonld_by_id(obj)
    assert result == ["a", "b", "c"]


def test_sort_jsonld_by_id_mixed_list() -> None:
    """Test that mixed lists (not all dicts with @id) are not sorted."""
    obj = [
        {"@id": "http://example.org/z", "name": "Z"},
        "not a dict",
        {"@id": "http://example.org/a", "name": "A"},
    ]
    result = sort_jsonld_by_id(obj)
    # Should not be sorted because not all items are dicts with @id
    assert result == [
        {"@id": "http://example.org/z", "name": "Z"},
        "not a dict",
        {"@id": "http://example.org/a", "name": "A"},
    ]


def test_sort_jsonld_by_id_list_without_all_ids() -> None:
    """Test that lists where not all dicts have @id are not sorted."""
    obj = [
        {"@id": "http://example.org/z", "name": "Z"},
        {"name": "no id"},
        {"@id": "http://example.org/a", "name": "A"},
    ]
    result = sort_jsonld_by_id(obj)
    # Should not be sorted because not all items have @id
    assert result == [
        {"@id": "http://example.org/z", "name": "Z"},
        {"name": "no id"},
        {"@id": "http://example.org/a", "name": "A"},
    ]


def test_sort_jsonld_by_id_primitive_values() -> None:
    """Test that primitive values are returned unchanged."""
    assert sort_jsonld_by_id("string") == "string"
    assert sort_jsonld_by_id(123) == 123
    assert sort_jsonld_by_id(True) is True
    assert sort_jsonld_by_id(None) is None


def test_sort_jsonld_by_id_empty_dict() -> None:
    """Test sorting an empty dict."""
    obj: dict[str, Any] = {}
    result = sort_jsonld_by_id(obj)
    assert result == {}
