"""Buffer yields from a string generator."""

from collections.abc import Callable, Generator, Iterable
from functools import wraps
from typing import Any, cast


def buffered[T: Callable[..., Iterable[str]]](size: int = 8192) -> Callable[[T], T]:
    """Combine successive string yields into chunks of at least ``size`` characters.

    The final chunk may be smaller than ``size``. Individual pieces larger than
    ``size`` are yielded as soon as they fill (or overflow) the buffer; they are
    not split further.

    Args:
        size: Minimum number of characters to accumulate before yielding a chunk.
            Must be positive.
            Defaults to 8192.

    """
    if size <= 0:
        msg = "buffer size must be positive"
        raise ValueError(msg)

    def decorator(fn: T) -> T:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Generator[str]:
            buf: list[str] = []
            length = 0
            for piece in fn(*args, **kwargs):
                buf.append(piece)
                length += len(piece)
                if length >= size:
                    yield "".join(buf)
                    buf.clear()
                    length = 0
            if buf:
                yield "".join(buf)

        return cast("T", wrapper)

    return decorator
