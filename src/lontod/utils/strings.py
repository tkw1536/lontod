"""generic strings utility functionality"""

from typing import Union


def as_utf8(value: Union[str, bytes]) -> bytes:
    """Turns a value into a utf-8 encoded set of bytes, unless it already is"""
    if isinstance(value, str):
        return value.encode("utf-8")
    return value
