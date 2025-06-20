"""test the strings module."""

import pytest

from lontod.utils import strings


@pytest.mark.parametrize(
    ("data", "want"),
    [("hello world", b"hello world"), (b"hello world", b"hello world")],
)
def test_as_utf8(data: str | bytes, want: bytes) -> None:
    """Test the as_utf8 function."""
    assert strings.as_utf8(data) == want
