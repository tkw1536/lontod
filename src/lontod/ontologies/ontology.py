"""Basic ontology definitions and utility functions"""

from dataclasses import dataclass
from os.path import basename, splitext
from typing import Generator, Tuple, final


@final
@dataclass
class Ontology:
    """Represents an ontology that can be indexed"""

    # URI Identifier of this ontology
    uri: str
    alternate_uris: list[str]

    @property
    def uris(self) -> Generator[tuple[str, bool]]:
        """all uris of this ontology"""
        yield self.uri, True
        for uri in self.alternate_uris:
            yield uri, False

    # map from media type to content of ontology
    encodings: dict[str, bytes]

    # list of (definiendum, fragment)
    definienda: list[Tuple[str, str]]

    @property
    def all_definienda(self) -> Generator[Tuple[str, str, bool], None, None]:
        """like definienda but with alternate uri replacements"""
        for uri, fragment in self.definienda:
            yield uri, fragment, True

            # find only relative concept uris
            if not uri.startswith(self.uri):
                continue
            relative = uri[len(self.uri) :]

            # yield each of the alternate uris
            for base in self.alternate_uris:
                yield base + relative, fragment, False


class NoOntologyFound(Exception):
    """Raised when no ontology is found"""


def slug_from_path(path: str) -> str:
    """Given a relative or absolute pathname, return a slug for the given ontology"""

    base, _ = splitext(basename(path))
    return base
