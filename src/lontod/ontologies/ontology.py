"""Basic ontology definitions and utility functions"""

from dataclasses import dataclass
from os.path import basename, splitext
from typing import Optional, Tuple, final


@final
@dataclass
class Ontology:
    """Represents an ontology that can be indexed"""

    # URI Identifier of this ontology
    uri: str

    # map from media type to content of ontology
    encodings: dict[str, bytes]

    # list of (definiendum, fragment)
    definienda: list[Tuple[str, Optional[str]]]


class NoOntologyFound(Exception):
    """Raised when no ontology is found"""


def slug_from_path(path: str) -> str:
    """Given a relative or absolute pathname, return a slug for the given ontology"""

    base, _ = splitext(basename(path))
    return base
