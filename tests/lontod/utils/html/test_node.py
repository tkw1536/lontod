"""Test the node module."""

import pytest

from lontod.utils.html import node


@pytest.mark.parametrize(
    ("n", "want"),
    [
        # empty
        (node.TextNode(""), ""),
        # not escaped
        (node.TextNode("i don't need escape"), "i don't need escape"),
        # escaped
        (node.TextNode("i need < escape"), "i need &lt; escape"),
    ],
)
def test_text_node(n: node.TextNode, want: str) -> None:
    """Test rendering a TextNode."""
    got = n.render()
    assert got == want


@pytest.mark.parametrize(
    ("n", "want"),
    [
        # empty
        (node.RawNode(""), ""),
        # balanced
        (node.RawNode("<test>something</test>"), "<test>something</test>"),
        # unbalanced
        (node.RawNode("<test>I'm not even balanced"), "<test>I'm not even balanced"),
    ],
)
def test_raw_node(n: node.RawNode, want: str) -> None:
    """Test rendering a RawNode."""
    got = n.render()
    assert got == want


@pytest.mark.parametrize(
    ("n", "want"),
    [
        # single argument
        (node.FragmentNode("test"), "test"),
        (node.FragmentNode(None), ""),
        (node.FragmentNode(node.RawNode("<hr>")), "<hr>"),
        (node.FragmentNode(("test", None, node.RawNode("<hr>"))), "test<hr>"),
        # multiple arguments
        (node.FragmentNode("test", None, node.RawNode("<hr>")), "test<hr>"),
    ],
)
def test_fragment_node(n: node.FragmentNode, want: str) -> None:
    """Test rendering a FragmentNode."""
    got = n.render()
    assert got == want


@pytest.mark.parametrize(
    ("n", "want"),
    [
        # tag name
        (node.ElementNode("test", ()), "<test></test>"),
        # case-sensitive tag name
        (node.ElementNode("TeST", ()), "<TeST></TeST>"),
        # regular attribute value
        (
            node.ElementNode("test", example="value"),
            '<test example="value"></test>',
        ),
        # quoted attribute value
        (
            node.ElementNode("test", msg='I have a "'),
            '<test msg="I have a &quot;"></test>',
        ),
        # value-less attribute
        (
            node.ElementNode("test", example=None),
            "<test example></test>",
        ),
        # true attribute
        (
            node.ElementNode("test", example=True),
            "<test example></test>",
        ),
        # false attribute
        (
            node.ElementNode("test", example=False),
            "<test></test>",
        ),
        # escaped attribute name
        (
            node.ElementNode("test", _class="my_class"),
            '<test class="my_class"></test>',
        ),
        # escaped attribute value
        (
            node.ElementNode("test", hello_world="content"),
            '<test hello-world="content"></test>',
        ),
        # multiple attributes
        (
            node.ElementNode(
                "test",
                hello="world",
                other=None,
            ),
            '<test hello="world" other></test>',
        ),
        # children
        (
            node.ElementNode(
                "test",
                node.ElementNode("child1"),
                node.ElementNode("child2"),
            ),
            "<test><child1></child1><child2></child2></test>",
        ),
        # children with None
        (
            node.ElementNode("test", None, node.ElementNode("hr"), "some more text"),
            "<test><hr></hr>some more text</test>",
        ),
    ],
)
def test_element_node(n: node.ElementNode, want: str) -> None:
    """Test rendering an ElementNode."""
    got = n.render()
    assert got == want


@pytest.mark.parametrize(
    ("n", "want"),
    [
        # tag name
        (node.VoidElementNode("test"), "<test>"),
        # case-sensitive tag name
        (node.VoidElementNode("TeST"), "<TeST>"),
        # regular attribute value
        (
            node.VoidElementNode("test", example="value"),
            '<test example="value">',
        ),
        # quoted attribute value
        (
            node.VoidElementNode("test", msg='I have a "'),
            '<test msg="I have a &quot;">',
        ),
        # value-less attribute
        (
            node.VoidElementNode("test", example=None),
            "<test example>",
        ),
        # true attribute
        (
            node.VoidElementNode("test", example=True),
            "<test example>",
        ),
        # false attribute
        (
            node.VoidElementNode("test", example=False),
            "<test>",
        ),
        # escaped attribute name
        (
            node.VoidElementNode("test", _class="my_class"),
            '<test class="my_class">',
        ),
        # escaped attribute value
        (
            node.VoidElementNode("test", hello_world="content"),
            '<test hello-world="content">',
        ),
        # multiple attributes
        (
            node.VoidElementNode(
                "test",
                hello="world",
                other=None,
            ),
            '<test hello="world" other>',
        ),
    ],
)
def test_void_node(n: node.VoidElementNode, want: str) -> None:
    """Test rendering a VoidElementNode."""
    got = n.render()
    assert got == want
