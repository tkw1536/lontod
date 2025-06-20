"""debounce a function."""

from collections.abc import Callable
from functools import wraps
from threading import Timer
from typing import Any, Final, cast

type Func = Callable[..., None]


def debounce(wait: float) -> Callable[[Func], Func]:
    """Ensure a function is called at most once within 'wait' seconds."""

    def decorator(fn: Func) -> Func:
        timers: Final[list[Timer | None]] = [None]

        @wraps(fn)
        def debounced(*args: Any, **kwargs: Any) -> None:
            # cancel the previous timer if it exists
            if timers[0] is not None:
                timers[0].cancel()

            # set a new timer
            timer = Timer(wait, fn, args=args, kwargs=kwargs)
            timer.start()
            timers[0] = timer

        return cast("Func", debounced)

    return decorator
