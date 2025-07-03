"""Test the render module."""

import pytest

from lontod.html import render


@pytest.mark.parametrize(
    ("token", "want"),
    [
        # tag name
        (render.StartTagToken("test", ()), "<test>"),
        # case-sensitive tag name
        (render.StartTagToken("TeST", ()), "<TeST>"),
        # invalid tag name
        (render.StartTagToken("<invalid", ()), None),
        # regular attribute value
        (
            render.StartTagToken("test", (("example", "value"),)),
            '<test example="value">',
        ),
        # quoted attribute value
        (
            render.StartTagToken("test", (("msg", 'I have a "'),)),
            '<test msg="I have a &quot;">',
        ),
        # value-less attribute
        (
            render.StartTagToken("test", (("example", None),)),
            "<test example>",
        ),
        # invalid attribute name
        (
            render.StartTagToken("test", (("invalid>name", "test"),)),
            None,
        ),
        # multiple values
        (
            render.StartTagToken(
                "test",
                (("hello", "world"), ("other", None)),
            ),
            '<test hello="world" other>',
        ),
        # repeated value invalid
        (
            render.StartTagToken(
                "test",
                (("example", "value"), ("example", "second value")),
            ),
            None,
        ),
    ],
)
def test_start_tag_token(token: render.StartTagToken, want: str | None) -> None:
    """Test the StartTagToken class."""
    if want is None:
        with pytest.raises(render._InvalidError):  # noqa: SLF001
            _ = "".join(token.render())
        return

    got = "".join(token.render())
    assert got == want


@pytest.mark.parametrize(
    ("token", "want"),
    [
        # tag name
        (render.EndTagToken("test"), "</test>"),
        # case-sensitive tag name
        (render.EndTagToken("TeST"), "</TeST>"),
        # invalid tag name
        (render.EndTagToken("<invalid"), None),
    ],
)
def test_end_tag_token(token: render.EndTagToken, want: str | None) -> None:
    """Test the EndTagToken class."""
    if want is None:
        with pytest.raises(render._InvalidError):  # noqa: SLF001
            _ = "".join(token.render())
        return

    got = "".join(token.render())
    assert got == want


@pytest.mark.parametrize(
    ("token", "want"),
    [
        # empty
        (render.TextToken(""), ""),
        # not escaped
        (render.TextToken("i don't need escape"), "i don't need escape"),
        # escaped
        (render.TextToken("i need < escape"), "i need &lt; escape"),
    ],
)
def test_text_token(token: render.TextToken, want: str) -> None:
    """Test the TextToken class."""
    got = "".join(token.render())
    assert got == want


@pytest.mark.parametrize(
    ("token", "want"),
    [
        # empty
        (render.RawToken(""), ""),
        # balanced
        (render.RawToken("<test>something</test>"), "<test>something</test>"),
        # unbalanced
        (render.RawToken("<test>I'm not even balanced"), "<test>I'm not even balanced"),
    ],
)
def test_raw_token(token: render.RawToken, want: str) -> None:
    """Test the RawToken class."""
    got = "".join(token.render())
    assert got == want
