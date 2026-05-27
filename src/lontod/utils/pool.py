"""Implements a pool that recycles objects when needed."""

from collections import deque
from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from threading import Lock
from typing import Any


class Pool[T]:
    """Pool holds and manages a set of recyclable objects."""

    _q: deque[T]
    _maxsize: int
    _lock: Lock
    _sync: AbstractContextManager[Any]
    _setup: Callable[[], T]
    _reset: Callable[[T], None]
    _teardown: Callable[[T], None]

    def __init__(
        self,
        size: int,
        setup: Callable[[], T],
        reset: Callable[[T], None] | None,
        teardown: Callable[[T], None] | None,
        sync_manager: AbstractContextManager[Any] | None = None,
    ) -> None:
        """Create a new pool.

        Args:
        size (int): Number of items to keep alive in the pool
        setup (Callable[[], T]): Called to create a new pool item
        reset (Optional[Callable[[T], None]]): Called right before an item is returned to the pool
        teardown (Optional[Callable[[T], None]]): Called when an item is removed from the pool
        sync_manager (Optional[AbstractContextManager[Any]]): A context manager that is used to synchronize access to the pool. It will be used as long as some operation is performed on the pool.

        """
        self._q = deque()
        self._maxsize = size
        self._lock = Lock()
        self._sync = nullcontext() if sync_manager is None else sync_manager
        self._setup = setup
        self._reset = reset if reset is not None else lambda _: None
        self._teardown = teardown if teardown is not None else lambda _: None

    @contextmanager
    def use(self) -> Generator[T]:
        """Context manager that allows using an item from a pool."""
        with self._sync:
            item = self.__get()
            yield item
            self.__put(item)

    def __get(self) -> T:
        """Get an object from the pool, or (if empty) creates a new object."""
        with self._lock:
            if len(self._q) == 0:
                return self._setup()
            return self._q.popleft()

    def __put(self, item: T) -> None:
        """Return an object to the pool or (if it is full) discards it."""
        self._reset(item)

        with self._lock:
            if len(self._q) == self._maxsize:
                self._teardown(item)
                return
            self._q.append(item)

    def teardown(self) -> None:
        """Remove all objects from the pool."""
        with self._sync, self._lock:
            while len(self._q) > 0:
                self._teardown(self._q.popleft())


# spellchecker:words popleft
