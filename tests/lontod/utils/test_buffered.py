"""test the buffered module."""

import pytest

from lontod.utils.buffered import buffered


def test_buffered_combines_small_pieces() -> None:
    """Small successive yields are joined until the buffer size is reached."""

    @buffered(5)
    def gen() -> list[str]:
        return ["a", "b", "c", "d", "e", "f"]

    assert list(gen()) == ["abcde", "f"]


def test_buffered_flushes_remainder() -> None:
    """Any leftover content shorter than the buffer size is yielded at the end."""

    @buffered(4)
    def gen() -> list[str]:
        return ["abcd", "xy"]

    assert list(gen()) == ["abcd", "xy"]


def test_buffered_joins_until_size() -> None:
    """Pieces are accumulated until the buffer reaches the configured size."""

    @buffered(10)
    def gen() -> list[str]:
        return ["hello", "world"]

    assert list(gen()) == ["helloworld"]


def test_buffered_oversized_piece() -> None:
    """A single piece larger than the buffer size is yielded without being split."""

    @buffered(3)
    def gen() -> list[str]:
        return ["ab", "cdefgh", "ij"]

    assert list(gen()) == ["abcdefgh", "ij"]


def test_buffered_empty() -> None:
    """An empty iterable yields nothing."""

    @buffered(8)
    def gen() -> list[str]:
        return []

    assert list(gen()) == []


def test_buffered_preserves_joined_content() -> None:
    """Buffering must not change the concatenated output."""

    @buffered(4)
    def gen() -> list[str]:
        return ["<", "tag", " ", 'a="b"', ">", "text", "</", "tag", ">"]

    chunks = list(gen())
    assert "".join(chunks) == '<tag a="b">text</tag>'
    assert all(len(c) >= 4 or c is chunks[-1] for c in chunks)


def test_buffered_rejects_non_positive_size() -> None:
    """Buffer size must be positive."""
    with pytest.raises(ValueError, match="buffer size must be positive"):
        buffered(0)
    with pytest.raises(ValueError, match="buffer size must be positive"):
        buffered(-1)
