"""Holds RenderContext."""

from abc import ABC, abstractmethod
from collections.abc import Generator
from hashlib import md5
from typing import Final

from dominate.tags import (
    html_tag,
)
from rdflib.term import Node, URIRef


class HTMLable(ABC):
    """Represents an object that can be rendered as html."""

    @abstractmethod
    def to_html(self, ctx: "RenderContext") -> html_tag:
        """Turn this class into html."""


class RenderContext:
    """context used for rendering."""

    __fids: dict[URIRef, str]
    __fid_values: set[str]

    MAX_FID_TRIES: Final = 1000

    def __init__(self) -> None:
        """Create a new RenderContext."""
        self.__fids = {}
        self.__fid_values = set()

    def close(self) -> None:
        """Close this context, reserved for future usage."""

    def fragment(self, iri: URIRef, title: Node | None = None) -> str:
        """Return a fragment identifier for this title, using the given title node if it exists."""
        # already have a fragment identifier!
        if iri in self.__fids:
            return self.__fids[iri]

        # iterate through the candidates until we find a new one!
        the_fid: str
        for count, fid in enumerate(self.__fragment(iri, title)):
            if count == RenderContext.MAX_FID_TRIES:
                msg = "exceeded maximum tries when generating fragment identifier for {uri!r}"
                raise OverflowError(msg)
            if fid not in self.__fid_values:
                the_fid = fid
                break

        # cache and return
        self.__fids[iri] = the_fid
        if isinstance(the_fid, str):
            self.__fid_values.add(the_fid)

        # return the fid
        return the_fid

    def __fragment(self, uri: URIRef, title: Node | None = None) -> Generator[str]:
        """Yield possible fragment identifiers, repeating with a suffix if needed to allow for uniqueness."""
        pure_identifiers: list[str] = []

        for identifier in self.__fragment_pure(uri, title=title):
            yield identifier
            pure_identifiers.append(identifier)

        # fallback to the hash of the URI
        if len(pure_identifiers) == 0:
            md5_hash = md5(str(uri).encode("utf-8"), usedforsecurity=False)
            pure_identifiers = [md5_hash.hexdigest()]

        suffix = 1
        while True:
            suffix += 1
            for identifier in pure_identifiers:
                yield f"{identifier}_{suffix}"

    def __fragment_pure(self, uri: URIRef, title: Node | None = None) -> Generator[str]:
        s_iri = str(uri) if uri is not None else None
        s_title_ = str(title) if title is not None else None

        # try creating a fid from the label
        if s_title_ is not None:
            yield _remove_non_ascii_chars(s_title_.replace(" ", ""))

        # split URI for last slash segment
        segments = s_iri.split("/")
        if len(segments[-1]) < 1:
            return

        # don't allow domains ['http:', '', '{domain}']),
        if len(segments) < 4:  # noqa: PLR2004
            return

        # ends with only a '#'
        if segments[-1].endswith("#"):
            return

        fid = (
            segments[-1].split("#")[-1]
            if segments[-1].split("#")[-1] != ""
            else segments[-1].split("#")[-2]
        )

        # the fid itself (if it isn't yet set)
        yield fid


def _remove_non_ascii_chars(s_: str) -> str:
    return "".join(j for j in s_ if ord(j) < 128).replace("&", "")  # noqa: PLR2004
