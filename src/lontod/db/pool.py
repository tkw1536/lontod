from queue import Empty, Full, Queue
from threading import Lock
from types import TracebackType
from typing import Callable, Generic, Optional, Type, TypeVar

T = TypeVar("T")


class Pool(Generic[T]):
    """Pool does stuff"""

    def __init__(
        self, size: int, setup: Callable[[], T], teardown: Optional[Callable[[T], None]]
    ):
        self._q = Queue(maxsize=size)
        self._lock = Lock()
        self._setup = setup
        self._teardown = teardown if teardown is not None else lambda x: None

    def use(self) -> "PoolContextManager[T]":
        return PoolContextManager(self)

    def get(self) -> T:
        with self._lock:
            try:
                return self._q.get_nowait()
            except Empty:
                return self._setup()

    def put(self, item: T) -> T:
        with self._lock:
            try:
                self._q.put_nowait(item)
            except Full:  # don't want to keep it!
                return self._teardown(item)

    def teardown(self):
        with self._lock:
            while not self._q.empty():
                self._teardown(self._q.get_nowait())


class PoolContextManager(Generic[T]):
    def __init__(self, pool: Pool[T]):
        self._pool = pool
        self._item = None

    def __enter__(self) -> T:
        self._item = self._pool.get()
        return self._item

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> bool:
        self._pool.put(self._item)
        self._item = None  # prevent memory leakage
        return False
