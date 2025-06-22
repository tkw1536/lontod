"""test the debounce module."""

from threading import Timer
from threading import enumerate as enumerate_threads
from time import sleep

from lontod.utils import debounce


def test_debounce() -> None:
    """Test the debounce decorator."""
    invoke_count = 0
    argument: int | None = None

    @debounce.debounce(0.1)
    def do_something(arg: int) -> None:
        nonlocal invoke_count, argument
        invoke_count += 1
        argument = arg

    # invoke the function several times
    do_something(1)
    do_something(2)
    do_something(3)

    # wait for the timers to have fired
    _wait_timer_threads()

    # check that the function was only called once
    # and with the right argument
    assert invoke_count == 1
    assert argument == 3


def _wait_timer_threads() -> None:
    """Wait for all threading.Timer threads to finish."""
    while True:
        for thread in enumerate_threads():
            if isinstance(thread, Timer):
                break
        else:
            return

        sleep(0.1)
