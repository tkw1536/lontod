"""HTML Rendering."""

import re
from abc import ABC, abstractmethod
from collections.abc import Generator, Sequence
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
class RepeatedAttributeError(_InvalidError):
    """Indicates that an attribute value was repeated."""


@final
class InvalidTagNameError(_InvalidError):
    """Indicates an invalid tag name."""

    REGEX = re.compile(r"^[a-zA-Z][a-zA-Z0-9-_\.]*$")


@final
class InvalidAttributeNameError(_InvalidError):
    """Indicates an invalid attribute name."""

    REGEX = re.compile(r'^([^\t\n\f \/>"\'=]+)$')


type Token = "StartTagToken|EndTagToken|TextToken|RawToken"
"""Token used during html rendering."""


class _BaseToken(ABC):
    @abstractmethod
    def render(self) -> Generator[str]:
        """Render this token into a string."""


@final
@dataclass
class StartTagToken(_BaseToken):
    """Represents a start tag."""

    tag_name: str
    attributes: Sequence[tuple[str, str | None]]

    @override
    def render(self) -> Generator[str]:
        yield "<"

        InvalidTagNameError.assert_valid(self.tag_name)
        yield self.tag_name

        seen = set[str]()
        for name, value in self.attributes:
            norm_name = name.lower()
            if norm_name in seen:
                msg = f"attribute {name!r} repeated"
                raise RepeatedAttributeError(msg)
            seen.add(norm_name)

            yield " "

            InvalidAttributeNameError.assert_valid(name)
            yield name

            if not isinstance(value, str):
                continue

            yield '="'
            yield escape(value, quote=True)
            yield '"'

        yield ">"


@final
@dataclass(frozen=True)
class EndTagToken(_BaseToken):
    """Represents a close tag."""

    tag_name: str

    @override
    def render(self) -> Generator[str]:
        InvalidTagNameError.assert_valid(self.tag_name)

        yield "</"
        yield self.tag_name
        yield ">"


@final
@dataclass(frozen=True)
class TextToken(_BaseToken):
    """Represents text content."""

    content: str

    @override
    def render(self) -> Generator[str]:
        yield escape(self.content, quote=False)


@final
@dataclass(frozen=True)
class RawToken(_BaseToken):
    """An unsafe token that does not escape."""

    html: str

    @override
    def render(self) -> Generator[str]:
        yield self.html
