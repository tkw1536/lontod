"""Holds the intersperse function."""

from collections.abc import Generator, Iterable


def intersperse[T,U](it: Iterable[T], sep: U) -> Generator[T|U]:
    """Intersperses the given iterable with instances of sep."""
    first = True
    for elem in it:
        if not first:
            yield sep
        else:
            first = False

        yield elem
