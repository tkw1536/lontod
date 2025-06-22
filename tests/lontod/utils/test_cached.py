"""test the cached module."""

from lontod.utils import cached

# spellchecker:words picklecachedmeta


class Whatever(metaclass=cached.PickleCachedMeta):
    """A class for testing."""

    global_counter: int = 0
    counter: int

    def __init__(self) -> None:
        """Create a new Whatever."""
        self.counter = Whatever.global_counter
        Whatever.global_counter += 1


def test_picklecachedmeta() -> None:
    """Test the PickleCachedMeta class."""
    # first instantiation invokes the init function
    w1 = Whatever()
    assert w1.counter == 0
    assert Whatever.global_counter == 1

    # second instantiation returns a copy
    w2 = Whatever()
    assert w2.counter == 0

    # they are different instances
    assert w1 is not w2
