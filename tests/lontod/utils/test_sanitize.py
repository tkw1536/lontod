"""Test the sanitize module."""

import pytest

from lontod.utils import sanitize


@pytest.mark.parametrize(
    ("html", "want"),
    [
        (
            "hello world",
            "hello world",
        ),
        (
            "<b>safe html</b>",
            "<b>safe html</b>",
        ),
        (
            "some text with \t      weird spaces\t",
            "some text with \t      weird spaces\t",
        ),
        (
            "unsafe html<script>alert('unsafe');</script>",
            "unsafe html",
        ),
    ],
)
def test_sanitize(html: str, want: str) -> None:
    """Test the sanitize function."""
    assert sanitize.sanitize(html) == want
