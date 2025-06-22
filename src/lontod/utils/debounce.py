"""debounce a function."""

from collections.abc import Callable
from functools import wraps
from threading import Lock, Timer
from typing import Any, cast

type Func = Callable[..., None]


def debounce(wait: float) -> Callable[[Func], Func]:
    """Ensure a function is called only if no new calls are made to it within wait seconds.

    The decorated function is safe to be called concurrently by multiple threads.
    It is invoked on a separate thread using a threading.Timer, with the arguments
    (positional and keyword) of the latest invocation.
    """

    def decorator(fn: Func) -> Func:
        timer: Timer | None = None
        lock: Lock = Lock()

        @wraps(fn)
        def debounced(*args: Any, **kwargs: Any) -> None:
            nonlocal timer, lock
            with lock:
                if timer is not None:
                    timer.cancel()

                timer = Timer(wait, fn, args=args, kwargs=kwargs)
                timer.start()

        return cast("Func", debounced)

    return decorator
