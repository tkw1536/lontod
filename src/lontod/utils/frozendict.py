"""Implements frozendict."""

from collections.abc import Iterable, Iterator, Mapping
from threading import Lock
from typing import TypeVar, overload

KT = TypeVar("KT")
VT_co = TypeVar("VT_co", covariant=True)


class FrozenDict(Mapping[KT, VT_co]):
    """An immutable dict subtype that cannot be modified."""

    # NOTE: This class might need to be considered immutable by ruff and friends.
    # This can be achieved with a section like the following in pyproject.toml:
    #
    # [tool.ruff.lint.flake8-bugbear]
    # extend-immutable-calls = ["lontod.utils.frozendict.FrozenDict"]
    #
    # This might need to be kept in sync with the name of this class.

    __dict: dict[KT, VT_co]

    # lots of overloads -- to be type-compatible with the standard dict
    @overload
    def __init__(self) -> None: ...
    @overload
    def __init__(self: "FrozenDict[str, VT_co]", **kwargs: VT_co) -> None: ...
    @overload
    def __init__(self, mp: "Mapping[KT, VT_co]", /) -> None: ...
    @overload
    def __init__(
        self: "FrozenDict[str, VT_co]", mp: "Mapping[str, VT_co]", /, **kwargs: VT_co
    ) -> None: ...
    @overload
    def __init__(self, iterable: Iterable[tuple[KT, VT_co]], /) -> None: ...
    @overload
    def __init__(
        self: "FrozenDict[str, VT_co]",
        iterable: Iterable[tuple[str, VT_co]],
        /,
        **kwargs: VT_co,
    ) -> None: ...
    @overload
    def __init__(
        self: "FrozenDict[str, str]", iterable: Iterable[list[str]], /
    ) -> None: ...
    @overload
    def __init__(
        self: "FrozenDict[bytes, bytes]", iterable: Iterable[list[bytes]], /
    ) -> None: ...

    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Create a new frozen dictionary."""
        self.__dict = dict(*args, **kwargs)
        self._l = Lock()
        self._hash = None

    def __iter__(self) -> Iterator[KT]:
        """Iterate through the items in this dictionary."""
        return iter(self.__dict)

    def __getitem__(self, key: KT) -> VT_co:
        """Get an item from this dictionary."""
        return self.__dict[key]

    def __len__(self) -> int:
        """Total number of items in this dictionary."""
        return len(self.__dict)

    _l: Lock
    """protect _hash"""

    _hash: int | None
    """holds a cached hash"""

    def __hash__(self) -> int:
        """Compute the hash of the underlying items."""
        with self._l:
            if self._hash is None:
                self._hash = hash(tuple(sorted(self.__dict.items())))
            return self._hash
