"""Holds RenderContext."""

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Generator, Sequence
from hashlib import md5
from typing import TYPE_CHECKING, Final

from dominate.tags import (
    html_tag,
)
from rdflib.term import Node, URIRef

if TYPE_CHECKING:
    from .ontology import Ontology


class HTMLable(ABC):
    """Represents an object that can be rendered as html."""

    @abstractmethod
    def to_html(self, ctx: "RenderContext") -> html_tag:
        """Turn this class into html."""


class RenderContext:
    """context used for rendering."""

    __fids: dict[str, dict[URIRef, str]]
    __fid_values: set[str]

    MAX_FID_TRIES: Final = 1000

    def __init__(
        self,
        ontology: "Ontology",
        language_preferences: Sequence[None | str] = (None, "en"),
    ) -> None:
        """Create a new RenderContext."""
        self.__ontology = ontology
        self.__fids = defaultdict(dict)
        self.__fid_values = set()
        self.__language_preferences = {
            lang: i for (i, lang) in enumerate(language_preferences)
        }

    __ontology: "Ontology"

    @property
    def ontology(self) -> "Ontology":
        """Return the ontology that is used in this RenderContext."""
        return self.__ontology

    def language_preference(self, lang: str | None) -> int:
        """Return an integer representing the preference of a literal of the given language during rendering.
        The smaller the returned integer, the higher the preference.
        """
        try:
            return self.__language_preferences[lang]
        except KeyError:
            return len(self.__language_preferences)

    def close(self) -> None:
        """Close this context, reserved for future usage."""

    def fragment(self, iri: URIRef, title: Node | None = None, group: str = "") -> str:
        """Return a fragment identifier for this title, using the given title
        node if it exists.

        Identifiers for two different identifiers are guaranteed to be
        identical if and only if they originate from the same iri and are
        located in the same group.
        """
        # already have a fragment identifier!
        if iri in self.__fids[group]:
            return self.__fids[group][iri]

        # iterate through the candidates until we find a new one!
        the_fid: str
        for count, fid in enumerate(self.__fragment(iri, title)):
            if count == RenderContext.MAX_FID_TRIES:
                msg = "exceeded maximum tries when generating fragment identifier for {uri!r}"
                raise OverflowError(msg)

            candidate = fid if group == "" else f"{group}_" + fid
            if candidate not in self.__fid_values:
                the_fid = candidate
                break

        # cache the fid and store that we used it.
        self.__fids[group][iri] = the_fid
        self.__fid_values.add(the_fid)

        # return it!
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

        # the fid itself
        yield fid


def _remove_non_ascii_chars(s_: str) -> str:
    return "".join(j for j in s_ if ord(j) < 128).replace("&", "")  # noqa: PLR2004
