"""Sanitize some html."""

from typing import cast

from html_sanitizer.sanitizer import (
    Sanitizer,
    sanitize_href,
)

_SANITIZE_SETTINGS = {
    "tags": [
        "a",
        "b",
        "br",
        "em",
        "h1",
        "h2",
        "h3",
        "hr",
        "i",
        "li",
        "ol",
        "p",
        "strong",
        "sub",
        "sup",
        "ul",
    ],
    "attributes": {"a": ("href", "name", "target", "title", "rel")},
    "empty": {"hr", "a", "br"},
    "separate": {"a", "p", "li"},
    "whitespace": {"br"},
    "keep_typographic_whitespace": True,
    "add_nofollow": False,
    "autolink": False,
    "sanitize_href": sanitize_href,
    "element_preprocessors": [],
    "element_postprocessors": [],
}

_sanitizer = Sanitizer(_SANITIZE_SETTINGS)


def sanitize(html: str) -> str:
    """Sanitize html."""
    return cast("str", _sanitizer.sanitize(html))
