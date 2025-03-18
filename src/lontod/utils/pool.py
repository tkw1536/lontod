"""Implements a pool that recycles objects when needed"""

from collections import deque
from threading import Lock
from types import TracebackType
from typing import Callable, Generic, Literal, Optional, Type, TypeVar

T = TypeVar("T")


class Pool(Generic[T]):
    """Pool holds and manages a set of recyclable objects"""

    _q: deque[T]
    _maxsize: int
    _lock: Lock
    _setup: Callable[[], T]
    _reset: Callable[[T], None]
    _teardown: Callable[[T], None]

    def __init__(
        self,
        size: int,
        setup: Callable[[], T],
        reset: Optional[Callable[[T], None]],
        teardown: Optional[Callable[[T], None]],
    ):
        """
        Args:
            size (int): Number of items to keep alive in the pool
            setup (Callable[[], T]): Called to create a new pool item
            reset (Optional[Callable[[T], None]]): Called right before an item is returned to the pool
            teardown (Optional[Callable[[T], None]]): Called when an item is removed from the pool
        """
        self._q = deque()
        self._maxsize = size
        self._lock = Lock()
        self._setup = setup
        self._reset = reset if reset is not None else lambda _: None
        self._teardown = teardown if teardown is not None else lambda _: None

    def use(self) -> "PoolContextManager[T]":
        """A context manager that allows using an item from a pool"""
        return PoolContextManager(self)

    def get(self) -> T:
        """Gets an object from the pool, or (if empty) creates a new object"""
        with self._lock:
            if len(self._q) == 0:
                return self._setup()
            return self._q.popleft()

    def put(self, item: T) -> None:
        """Returns an object to the pool or (if it is full) discards it"""
        self._reset(item)

        with self._lock:
            if len(self._q) == self._maxsize:
                self._teardown(item)
                return
            self._q.append(item)

    def teardown(self) -> None:
        """Removes all objects from the pool"""
        with self._lock:
            if len(self._q) > 0:
                self._teardown(self._q.popleft())


class PoolContextManager(Generic[T]):
    """Allows a Pool to be used as a Context Manager"""

    _item: T
    _pool: Pool[T]

    def __init__(self, pool: Pool[T]):
        self._pool = pool

    def __enter__(self) -> T:
        self._item = self._pool.get()
        return self._item

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Literal[False]:
        self._pool.put(self._item)
        return False


# spellchecker:words popleft
