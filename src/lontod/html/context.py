"""Holds RenderContext."""

from collections.abc import Generator
from typing import Final

from rdflib.term import Node, URIRef


class RenderContext:
    """context used for rendering."""

    __fids: dict[URIRef, str | None]
    __fid_values: set[str]

    MAX_FID_TRIES: Final = 1000

    def __init__(self) -> None:
        """Create a new RenderContext."""
        self.__fids = {}
        self.__fid_values = set()

    def close(self) -> None:
        """Close this context, reserved for future usage."""

    def fragment(self, uri: URIRef, title: Node | None = None) -> str | None:
        """Return a fragment identifier for this uri, using the given title node if it exists."""
        # already have a fragment identifier!
        if uri in self.__fids:
            return self.__fids[uri]

        # iterate through the candidates until we find a new one!
        the_fid: str | None = None
        for count, fid in enumerate(self.__fragment(uri, title)):
            if count == RenderContext.MAX_FID_TRIES:
                msg = "exceeded maximum tries when generating fragment identifier for {uri!r}"
                raise OverflowError(msg)
            if fid not in self.__fid_values:
                the_fid = fid
                break

        # cache and return
        self.__fids[uri] = the_fid
        if isinstance(the_fid, str):
            self.__fid_values.add(the_fid)

        # return the fid
        return the_fid

    def __fragment(self, uri: URIRef, title: Node | None = None) -> Generator[str]:
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

        # add a counter
        counter = 1
        while True:
            yield f"{fid}{counter}"


def _remove_non_ascii_chars(s_: str) -> str:
    return "".join(j for j in s_ if ord(j) < 128).replace("&", "")  # noqa: PLR2004
