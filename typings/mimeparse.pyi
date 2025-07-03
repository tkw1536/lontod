__version__: str
__credits__: str

from collections.abc import Iterable

type _MediaRange = tuple[str, str, dict[str, str]]
type _MimeType = tuple[str, str, dict[str, str]]

class MimeTypeParseException(ValueError): ...  # noqa: N818

def parse_mime_type(mime_type: str) -> _MimeType: ...
def parse_media_range(range: str) -> _MediaRange: ...  # noqa: A002
def quality_and_fitness_parsed(
    mime_type: str,
    parsed_ranges: Iterable[_MediaRange],
) -> tuple[float, int]: ...
def quality_parsed(mime_type: str, parsed_ranges: Iterable[_MediaRange]) -> float: ...
def quality(mime_type: str, ranges: str) -> float: ...
def best_match(supported: Iterable[str], header: str) -> str: ...
