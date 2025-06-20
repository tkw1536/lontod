"""generic strings utility functionality."""


def as_utf8(value: str | bytes) -> bytes:
    """Turn a value into a utf-8 encoded set of bytes, unless it already is."""
    if isinstance(value, str):
        return value.encode("utf-8")
    return value
