"""HTML Rendering."""

import re
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape
from typing import ClassVar, final, override


class _InvalidError(ValueError, ABC):
    """Indicate invalid data guarded by pattern."""

    REGEX: ClassVar[re.Pattern[str]]

    @classmethod
    def assert_valid(cls, value: str) -> None:
        """Raise this error if the value is invalid."""
        if not cls.REGEX.fullmatch(value):
            raise cls


@final
class InvalidTagNameError(_InvalidError):
    """Indicates an invalid tag name."""

    REGEX = re.compile(r"^[a-zA-Z][a-zA-Z0-9-_\.]*$")


@final
class InvalidAttributeNameError(_InvalidError):
    """Indicates an invalid attribute name."""

    REGEX = re.compile(r'^([^\t\n\f \/>"\'=]+)$')


class _HTMLToken(ABC):
    @abstractmethod
    def render(self) -> str:
        """Render this token into a string."""


@final
@dataclass
class StartTagToken(_HTMLToken):
    """Represents a start tag."""

    tag_name: str
    attributes: Sequence[tuple[str, str | None]]

    @override
    def render(self) -> str:
        buffer: str = "<"

        InvalidTagNameError.assert_valid(self.tag_name)
        buffer += self.tag_name

        for name, value in self.attributes:
            buffer += " "

            InvalidAttributeNameError.assert_valid(name)
            buffer += name

            if not isinstance(value, str):
                continue

            buffer += f'="{escape(value, quote=True)}"'

        buffer += ">"

        return buffer


@final
@dataclass(frozen=True)
class EndTagToken(_HTMLToken):
    """Represents a close tag."""

    tag_name: str

    @override
    def render(self) -> str:
        InvalidTagNameError.assert_valid(self.tag_name)
        return f"</{self.tag_name}>"


@final
@dataclass(frozen=True)
class TextToken(_HTMLToken):
    """Represents text content."""

    content: str

    @override
    def render(self) -> str:
        return escape(self.content, quote=False)


@final
@dataclass(frozen=True)
class RawToken(_HTMLToken):
    """An unsafe token that does not escape."""

    html: str

    @override
    def render(self) -> str:
        return self.html
