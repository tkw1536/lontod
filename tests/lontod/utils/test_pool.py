"""test the pool module."""

from lontod.utils import pool


def test_pool() -> None:
    """Test the pool class."""
    counter = 0
    events: list[str] = []

    def setup() -> int:
        nonlocal events, counter

        t = counter
        counter += 1

        events.append(f"setup {t}")
        return t

    def reset(t: int) -> None:
        events.append(f"reset {t}")

    def teardown(t: int) -> None:
        events.append(f"teardown {t}")

    p = pool.Pool(1, setup, reset, teardown)

    # create a new object
    with p.use() as t:
        assert t == 0

    # re-use the object
    with p.use() as t:
        assert t == 0

    # use it once again
    with p.use() as t0:
        assert t0 == 0

        # use a second object at the same time
        with p.use() as t1:
            assert t1 == 1

    # final re-use
    with p.use() as t:
        assert t == 1

    # destroy everything
    p.teardown()

    assert events == [
        # new object
        "setup 0",
        "reset 0",
        # re-use object
        "reset 0",
        # second object
        "setup 1",
        "reset 1",
        # return initial object
        "reset 0",
        "teardown 0",
        # re-use it again
        "reset 1",
        # final teardown
        "teardown 1",
    ]
