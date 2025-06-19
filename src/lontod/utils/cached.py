"""holds a utility to unfreeze a class"""

import pickle
from typing import Any, Generic, TypeVar, cast

T = TypeVar("T")


class PickleCachedMeta(type, Generic[T]):
    """A metaclass implementing singletons"""

    _instances: dict[type, bytes] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> T:
        if cls in cls._instances:
            clone = pickle.loads(cls._instances[cls])
            return cast(T, clone)

        instance = super().__call__(*args, **kwargs)
        cls._instances[cls] = pickle.dumps(instance)
        return cast(T, instance)
