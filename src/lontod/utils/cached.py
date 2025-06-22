"""holds a utility to unfreeze a class."""

import pickle
from threading import Lock
from typing import Any, ClassVar, TypeVar, cast

T = TypeVar("T")


class PickleCachedMeta[T](type):
    """A metaclass implementing singletons."""

    _instances: ClassVar[dict[type, bytes]] = {}
    _lock: ClassVar[Lock] = Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> T:
        """Create a new instance of this class."""
        with cls._lock:
            if cls in cls._instances:
                clone = pickle.loads(cls._instances[cls])  # noqa: S301
                return cast("T", clone)

            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = pickle.dumps(instance)
            return cast("T", instance)
