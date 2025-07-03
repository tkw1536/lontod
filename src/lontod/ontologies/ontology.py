"""Basic ontology definitions and utility functions."""

from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import final

from lontod.utils.frozendict import FrozenDict


@final
@dataclass(frozen=True)
class Ontology:
    """Represents an ontology that can be indexed."""

    # URI Identifier of this ontology
    uri: str
    alternate_uris: tuple[str, ...]

    @property
    def uris(self) -> Generator[tuple[str, bool]]:
        """All uris of this ontology."""
        yield self.uri, True
        for uri in self.alternate_uris:
            yield uri, False

    # map from media type to content of ontology
    encodings: FrozenDict[str, bytes]

    # list of (definiendum, fragment)
    definienda: FrozenDict[str, str]

    @property
    def all_definienda(self) -> Generator[tuple[str, str, bool]]:
        """Like definienda but with alternate uri replacements."""
        for uri, fragment in self.definienda.items():
            yield uri, fragment, True

            # find only relative concept uris
            if not uri.startswith(self.uri):
                continue
            relative = uri[len(self.uri) :]

            # yield each of the alternate uris
            for base in self.alternate_uris:
                yield base + relative, fragment, False


class NoOntologyFoundError(Exception):
    """Raised when no ontology is found."""


def slug_from_path(path: Path) -> str:
    """Given a relative or absolute pathname, return a slug for the given ontology."""
    return path.stem  # TODO: rework this later, maybe use the contents?
