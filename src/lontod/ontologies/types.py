"""media types and mappings"""

from typing import Iterable, Tuple

_FORMAT_TO_MEDIA_TYPES_ = {
    "xml": "application/rdf+xml",
    "n3": "text/n3",
    "turtle": "text/turtle",
    "nt": "text/plain",
    "trig": "application/trig",
    "json-ld": "application/ld+json",
    "hext": "application/x-ndjson",
}

_MEDIA_TYPE_TO_FORMATS = {v: k for (k, v) in _FORMAT_TO_MEDIA_TYPES_.items()}


def media_types() -> Iterable[Tuple[str, str]]:
    """Iterates over all (extension, media_type) pairs"""

    yield from _FORMAT_TO_MEDIA_TYPES_.items()


def extension_from_type(typ: str) -> str | None:
    """Given a media type, return an extension including a period"""

    if typ not in _MEDIA_TYPE_TO_FORMATS:
        return None
    return _MEDIA_TYPE_TO_FORMATS[typ]
