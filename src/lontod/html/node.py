"""HTML Nodes."""

from abc import ABC, abstractmethod
from collections.abc import Generator, Iterable, Sequence
from dataclasses import dataclass
from typing import final, override

from .render import EndTagToken, RawToken, StartTagToken, TextToken, Token

type Node = "TextNode|RawNode|ElementNode|FragmentNode"
"""A Node that can be rendered into HTML."""

type NodeLike = Node | str | None | Iterable["NodeLike"]
"""Anything that can be treated like a node.
When Node, the node is ignored.
"""


def to_nodes(*nodes: NodeLike) -> Generator[Node]:
    """Parse a sequence of node-like objects into a sequence of actual nodes."""
    for child_like in nodes:
        if child_like is None:
            continue

        if isinstance(child_like, str):
            yield TextNode(text=child_like)
            continue

        if isinstance(child_like, TextNode | RawNode | ElementNode | FragmentNode):
            yield child_like
            continue

        if isinstance(child_like, Iterable):
            yield FragmentNode(*child_like)
            continue

        msg = f"invalid node {child_like!r}"
        raise TypeError(msg)


class BaseNode(ABC):
    """A node that generates token for html rendering."""

    @abstractmethod
    def tokens(self) -> Generator[Token]:
        """Yield that tokens that make up this node."""

    @final
    def render(self) -> str:
        """Render this node into html."""
        return "".join(part for tok in self.tokens() for part in tok.render())


def stream_nodes(*nodes: NodeLike) -> Generator[str]:
    """Yield rendered tokens from the given NodeLike."""
    for node in to_nodes(nodes):
        for token in node.tokens():
            yield from token.render()


def render_nodes(*nodes: NodeLike) -> str:
    """Render rendered tokens into a single string."""
    return "".join(stream_nodes(*nodes))


@final
@dataclass(frozen=True)
class TextNode(BaseNode):
    """Text content."""

    text: str

    @override
    def tokens(self) -> Generator[Token]:
        yield TextToken(self.text)


@final
@dataclass(frozen=True)
class RawNode(BaseNode):
    """Raw unescaped html."""

    html: str

    @override
    def tokens(self) -> Generator[Token]:
        yield RawToken(self.html)


@final
@dataclass(frozen=True, init=False)
class FragmentNode(BaseNode):
    """A set of children grouped together."""

    children: Sequence[Node]

    def __init__(self, *children: NodeLike) -> None:
        """Create a new FragmentNode."""
        object.__setattr__(self, "children", tuple(to_nodes(*children)))

    @override
    def tokens(self) -> Generator[Token]:
        for node in self.children:
            yield from node.tokens()


type AttributeLike = str | bool | None
"""Anything that can be treated like an attribute.
True or None indicate an attribute without a value.
False attributes are omitted.
"""


def to_attributes(**attributes: AttributeLike) -> Generator[tuple[str, str | None]]:
    """Parse an attribute-like dictionary into actual attribute pairs.

    Use a leading "_" to escape reserved words in attribute names, e.g. "_class = 'my-class'".
    To set an attribute "_class", repeat the "_": "__class='I start with an underscore.'".
    Use _ instead of "-" in attribute names.
    """
    # TODO: Support "_" in attribute names.
    for attr, value in attributes.items():
        attr_name = attr.removeprefix("_").replace("_", "-")
        if isinstance(value, str | None):
            yield (attr_name, value)
            continue

        if isinstance(value, bool):
            if value:
                yield (attr_name, None)
            continue

        msg = f"invalid attribute value {value!r}"
        raise TypeError(msg)


@dataclass(frozen=True, init=False)
class ElementNode(BaseNode):
    """Represents an html node."""

    tag_name: str
    attributes: Sequence[tuple[str, str | None]]
    children: Sequence[Node]

    def __init__(
        self, tag_name: str, *children: NodeLike, **attributes: AttributeLike
    ) -> None:
        """Create a new ElementNode."""
        object.__setattr__(self, "tag_name", tag_name)
        object.__setattr__(self, "children", tuple(to_nodes(*children)))
        object.__setattr__(self, "attributes", tuple(to_attributes(**attributes)))

    @override
    def tokens(self) -> Generator[Token]:
        yield StartTagToken(self.tag_name, self.attributes)
        for child in self.children:
            yield from child.tokens()
        yield EndTagToken(self.tag_name)


@dataclass(frozen=True, init=False)
class VoidElementNode(ElementNode):
    """Represents an html void element, i.e. a node that cannot have any child nodes."""

    def __init__(self, tag_name: str, **attributes: AttributeLike) -> None:
        """Create a new ElementNode."""
        super().__init__(tag_name, **attributes)

    @override
    def tokens(self) -> Generator[Token]:
        yield StartTagToken(self.tag_name, self.attributes)


__all__ = [
    "AttributeLike",
    "ElementNode",
    "FragmentNode",
    "Node",
    "NodeLike",
    "RawNode",
    "TextNode",
    "VoidElementNode",
    "render_nodes",
    "stream_nodes",
]
