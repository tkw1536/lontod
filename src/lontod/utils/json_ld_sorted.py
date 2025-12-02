"""Sort JSON-LD output to make it deterministic."""

from typing import Any


def sort_jsonld_by_id(obj: Any, parent_key: str | None = None) -> Any:
    """Produce sorted json-ld output.

    Recursively walk JSON-LD and sort lists of node objects by @id,
    except when the list is under '@list' (where order is meaningful).
    """
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            obj[k] = sort_jsonld_by_id(v, parent_key=k)
        return obj

    if isinstance(obj, list):
        # First normalize children
        new_list = [sort_jsonld_by_id(v, parent_key=parent_key) for v in obj]

        # Do not reorder JSON-LD @list containers
        if parent_key == "@list":
            return new_list

        # If this looks like a list of JSON-LD nodes with @id, sort by @id
        if new_list and all(isinstance(v, dict) and "@id" in v for v in new_list):
            new_list.sort(key=lambda v: v.get("@id", ""))

        return new_list

    return obj
