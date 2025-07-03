"""Test the node module."""

import pytest

from lontod.html import elements


@pytest.mark.parametrize(
    ("n", "want"),
    [
        # tag name
        (elements.P(), "<p></p>"),
        # regular attribute value
        (
            elements.P(example="value"),
            '<p example="value"></p>',
        ),
        # quoted attribute value
        (
            elements.P(msg='I have a "'),
            '<p msg="I have a &quot;"></p>',
        ),
        # value-less attribute
        (
            elements.P(example=None),
            "<p example></p>",
        ),
        # true attribute
        (
            elements.P(example=True),
            "<p example></p>",
        ),
        # false attribute
        (
            elements.P(example=False),
            "<p></p>",
        ),
        # escaped attribute name
        (
            elements.P(_class="my_class"),
            '<p class="my_class"></p>',
        ),
        # escaped attribute value
        (
            elements.P(hello_world="content"),
            '<p hello-world="content"></p>',
        ),
        # multiple attributes
        (
            elements.P(
                hello="world",
                other=None,
            ),
            '<p hello="world" other></p>',
        ),
        # children
        (
            elements.P(
                elements.SPAN(),
                elements.SPAN(),
            ),
            "<p><span></span><span></span></p>",
        ),
        # children with None
        (
            elements.P(None, elements.SPAN(), "some more text"),
            "<p><span></span>some more text</p>",
        ),
    ],
)
def test_an_element(n: elements._Element, want: str) -> None:
    """Test rendering _Elements."""
    got = n.render()
    assert got == want


@pytest.mark.parametrize(
    ("n", "want"),
    [
        # tag name
        (elements.HR(), "<hr>"),
        # regular attribute value
        (
            elements.HR(example="value"),
            '<hr example="value">',
        ),
        # quoted attribute value
        (
            elements.HR(msg='I have a "'),
            '<hr msg="I have a &quot;">',
        ),
        # value-less attribute
        (
            elements.HR(example=None),
            "<hr example>",
        ),
        # true attribute
        (
            elements.HR(example=True),
            "<hr example>",
        ),
        # false attribute
        (
            elements.HR(example=False),
            "<hr>",
        ),
        # escaped attribute name
        (
            elements.HR(_class="my_class"),
            '<hr class="my_class">',
        ),
        # escaped attribute value
        (
            elements.HR(hello_world="content"),
            '<hr hello-world="content">',
        ),
        # multiple attributes
        (
            elements.HR(
                hello="world",
                other=None,
            ),
            '<hr hello="world" other>',
        ),
    ],
)
def test_void_element(n: elements._VoidElement, want: str) -> None:
    """Test rendering _VoidElement."""
    got = n.render()
    assert got == want
