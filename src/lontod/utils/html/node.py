"""HTML Nodes."""

from abc import ABC, abstractmethod
from collections.abc import Generator, Iterable, Sequence
from dataclasses import dataclass
from typing import final, override

from .render import EndTagToken, RawToken, StartTagToken, TextToken, _HTMLToken


class HTMLNode(ABC):
    """A html node."""

    @abstractmethod
    def tokens(self) -> Generator[_HTMLToken]:
        """Yield that tokens that make up this node."""

    @final
    def render(self) -> str:
        """Render this node into html."""
        return "".join(part for tok in self.tokens() for part in tok.render())


@final
@dataclass(frozen=True)
class TextNode(HTMLNode):
    """Text content."""

    text: str

    @override
    def tokens(self) -> Generator[_HTMLToken]:
        yield TextToken(self.text)


type AttributeLike = str | bool | None
"""Anything that can be treated like an attribute.
True or None indicate an attribute without a value.
False attributes are omitted.
"""


def to_attributes(**attributes: AttributeLike) -> Sequence[tuple[str, str | None]]:
    """Parse an attribute-like dictionary into actual attribute pairs.

    Use a leading "_" to escape reserved words in attribute names, e.g. "_class = 'my-class'".
    To set an attribute "_class", repeat the "_": "__class='I start with an underscore.'".
    Use _ instead of "-" in attribute names.
    """
    # TODO: Support "_" in attribute names.
    pairs: list[tuple[str, str | None]] = []
    for attr, value in attributes.items():
        attr_name = attr.removeprefix("_").replace("_", "-")
        if isinstance(value, str | None):
            pairs.append((attr_name, value))
            continue

        if isinstance(value, bool):
            if value:
                pairs.append((attr_name, None))
            continue

        msg = f"invalid attribute value {value!r}"
        raise TypeError(msg)

    return pairs


type NodeLike = Iterable["NodeLike"] | HTMLNode | str | None
"""Anything that can be treated like a node.
When Node, the node is ignored.
"""


def to_nodes(*nodes: NodeLike) -> Sequence[HTMLNode]:
    """Parse a sequence of node-like objects into a sequence of actual nodes."""
    node_list: list[HTMLNode] = []
    for child_like in nodes:
        if isinstance(child_like, str):
            node_list.append(TextNode(text=child_like))
            continue

        if isinstance(child_like, HTMLNode):
            node_list.append(child_like)
            continue

        if isinstance(child_like, Iterable):
            node_list.append(FragmentNode(*child_like))
            continue

        msg = f"invalid node {child_like!r}"
        raise TypeError(msg)
    return node_list


@final
@dataclass(frozen=True)
class RawNode(HTMLNode):
    """Raw unescaped html."""

    html: str

    @override
    def tokens(self) -> Generator[_HTMLToken]:
        yield RawToken(self.html)


@dataclass(frozen=True, init=False)
class ElementNode(HTMLNode):
    """Represents an html node."""

    tag_name: str
    attributes: Sequence[tuple[str, str | None]]
    children: Sequence[HTMLNode]

    def __init__(
        self, tag_name: str, *children: NodeLike, **attributes: AttributeLike
    ) -> None:
        """Create a new ElementNode."""
        object.__setattr__(self, "tag_name", tag_name)
        object.__setattr__(self, "children", to_nodes(*children))
        object.__setattr__(self, "attributes", to_attributes(**attributes))

    @override
    def tokens(self) -> Generator[_HTMLToken]:
        yield StartTagToken(self.tag_name, self.attributes)
        for child in self.children:
            yield from child.tokens()
        yield EndTagToken(self.tag_name)


@final
@dataclass(frozen=True, init=False)
class FragmentNode(HTMLNode):
    """A set of children grouped together."""

    children: Sequence[HTMLNode]

    def __init__(self, *children: NodeLike) -> None:
        """Create a new FragmentNode."""
        object.__setattr__(self, "children", to_nodes(*children))

    @override
    def tokens(self) -> Generator[_HTMLToken]:
        for node in self.children:
            yield from node.tokens()


__all__ = [
    "AttributeLike",
    "ElementNode",
    "FragmentNode",
    "HTMLNode",
    "NodeLike",
    "RawNode",
    "TextNode",
]
