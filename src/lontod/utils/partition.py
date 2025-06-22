"""Implements a partition function."""

from collections.abc import Callable, Generator, Iterable, Sequence


def partition[T, P](
    sequence: Iterable[T], predicate: Callable[[T], P]
) -> Generator[tuple[P, Sequence[T]]]:
    """Partitions the given iterable into distinct sequences based on predicate.

    The entire sequence must be held in memory.
    The returned generator is guaranteed to maintain order, both within a partition and across partitions.
    """
    keys: list[P] = []
    indexes: dict[P, int] = {}

    parts: list[list[T]] = []

    for elem in sequence:
        key = predicate(elem)

        try:
            index = indexes[key]
        except KeyError:
            index = len(keys)
            parts.append([])

            keys.append(key)
            indexes[key] = index

        parts[index].append(elem)

    for key, part in zip(keys, parts, strict=True):
        yield (key, part)
