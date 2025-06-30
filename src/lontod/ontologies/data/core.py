"""Holds RenderContext."""

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Generator
from enum import Enum, auto
from hashlib import md5
from typing import TYPE_CHECKING, Final, final

from markdown import markdown
from rdflib.term import Literal, Node, URIRef

from lontod.utils.html import (
    DIV,
    SUP,
    NodeLike,
    RawNode,
    render_nodes,
)
from lontod.utils.html import (
    Node as HTMLNode,
)
from lontod.utils.sanitize import sanitize

if TYPE_CHECKING:
    from .ontology import Ontology


class HTMLable(ABC):
    """Represents an object that can be rendered as html."""

    @final
    def html(self, ctx: "RenderContext") -> str:
        """Turn this HTMLable into a single html node."""
        return render_nodes(self.to_html(ctx))

    @abstractmethod
    def to_html(self, ctx: "RenderContext") -> NodeLike:
        """Turn this class into html."""
        # TODO: Make this private.


class ContentRendering(Enum):
    """How to render resource literal content."""

    SHOW_AS_TEXT = auto()
    SHOW_SANITIZED_MARKDOWN = auto()
    SHOW_RAW_MARKDOWN = auto()

    def __call__(self, lit: Literal) -> HTMLNode:
        """Render the given literal."""
        lang_sup = (
            SUP(
                str(lit.language),
                _class="sup-lang",
                lang="en",
            )
            if lit.language is not None
            else None
        )

        # TODO: Maybe do a check based on type here?
        content = str(lit.value)

        if self == ContentRendering.SHOW_AS_TEXT:
            return DIV(
                lang_sup,
                DIV(
                    content,
                    lang=lit.language,
                ),
            )

        # HACK: Prepend the lang_sup to the markdown to be rendered.
        if lang_sup is not None:
            content = lang_sup.render() + content

        # render the markdown
        md = markdown(content)

        # sanitize it!
        if self == ContentRendering.SHOW_SANITIZED_MARKDOWN:
            md = sanitize(md)

        return DIV(DIV(RawNode(md), lang=lit.language))


class RenderContext:
    """context used for rendering."""

    __fids: dict[str, dict[URIRef, str]]
    __fid_values: set[str]

    MAX_FID_TRIES: Final = 1000

    def __init__(
        self,
        ontology: "Ontology",
        content_rendering: ContentRendering = ContentRendering.SHOW_SANITIZED_MARKDOWN,
    ) -> None:
        """Create a new RenderContext."""
        self.__ontology = ontology
        self.__fids = defaultdict(dict)
        self.__fid_values = set()
        self.__iri_cache = {}
        self.__content_rendering = content_rendering

    __content_rendering: ContentRendering

    def render_content(self, lit: Literal) -> HTMLNode:
        """Render literal content."""
        return self.__content_rendering(lit)

    __ontology: "Ontology"

    @property
    def ontology(self) -> "Ontology":
        """Return the ontology that is used in this RenderContext."""
        return self.__ontology

    def close(self) -> None:
        """Close this context, reserved for future usage."""

    __iri_cache: dict[URIRef, str]

    def format_iri(self, iri: URIRef) -> str:
        """Format this IRI as a readable string."""
        short = self.__iri_cache.get(iri, None)
        if isinstance(short, str):
            return short

        short = self.__format_iri(iri)
        self.__iri_cache[iri] = short
        return short

    def __format_iri(self, iri: URIRef) -> str:
        longest_ns: tuple[str, URIRef] | None = None
        for short, long in self.ontology.namespaces:
            if not iri.startswith(long):
                continue
            if longest_ns is None:
                longest_ns = (short, long)
                continue
            if len(long) > len(longest_ns[1]):
                longest_ns = (short, long)
                continue

        if longest_ns is None:
            return str(iri)

        (short, long) = longest_ns
        return f"{short}:{iri[len(long) :]}"

    def fragment(self, iri: URIRef, /, group: str = "") -> str:
        """Return a fragment identifier for this title, using the given title node if it exists.

        Identifiers for two different identifiers are guaranteed to be
        identical if and only if they originate from the same iri and are
        located in the same group.
        """
        # already have a fragment identifier!
        if iri in self.__fids[group]:
            return self.__fids[group][iri]

        # iterate through the candidates until we find a new one!
        the_fid: str
        for count, fid in enumerate(self.__fragment(iri)):
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

    def __fragment(self, uri: URIRef) -> Generator[str]:
        """Yield possible fragment identifiers, repeating with a suffix if needed to allow for uniqueness."""
        pure_identifiers: list[str] = []

        for identifier in self.__fragment_pure(uri):
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
