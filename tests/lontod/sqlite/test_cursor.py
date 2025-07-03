"""Test the cursor module."""

from logging import DEBUG, getLogger
from sqlite3 import connect

import pytest

from lontod.sqlite.check import is_open
from lontod.sqlite.cursor import LoggingCursor, LoggingCursorContext

TEST_LOGGER = getLogger("test_logger")


def test_logging_cursor_context(caplog: pytest.LogCaptureFixture) -> None:
    """Test the logging cursor context."""
    caplog.set_level(level=DEBUG, logger=TEST_LOGGER.name)

    conn = connect("file:?mode=memory")

    try:
        with LoggingCursorContext(conn, TEST_LOGGER) as cursor:
            assert cursor.execute("CREATE TABLE example (data TEXT)") is cursor

        assert caplog.record_tuples == [
            (
                TEST_LOGGER.name,
                DEBUG,
                "execute('CREATE TABLE example (data TEXT)', ())",
            ),
            (
                TEST_LOGGER.name,
                DEBUG,
                "close()",
            ),
        ]
    finally:
        conn.close()


def test_logging_cursor(caplog: pytest.LogCaptureFixture) -> None:
    """Test the logging cursor."""
    caplog.set_level(level=DEBUG, logger=TEST_LOGGER.name)

    conn = connect("file:?mode=memory")
    try:
        cursor = LoggingCursor(conn, TEST_LOGGER)
        try:
            assert (
                cursor.executescript("CREATE TABLE whatever (something TEXT)") is cursor
            )

            assert cursor.execute("CREATE TABLE example (data TEXT)") is cursor

            assert (
                cursor.execute("INSERT INTO example (data) VALUES (?)", ("one",))
                is cursor
            )

            assert (
                cursor.executemany("INSERT INTO example (data) VALUES (?)", [("two",)])
                is cursor
            )
            assert (
                cursor.executemany(
                    "INSERT INTO example (data) VALUES (?)", [("three",), ("four",)]
                )
                is cursor
            )
            assert (
                cursor.executemany(
                    "INSERT INTO example (data) VALUES (?)",
                    [("five",), ("six",), ("seven",)],
                )
                is cursor
            )

            assert cursor.close() is None

            assert caplog.record_tuples == [
                (
                    TEST_LOGGER.name,
                    DEBUG,
                    "executescript('CREATE TABLE whatever (something TEXT)')",
                ),
                (
                    TEST_LOGGER.name,
                    DEBUG,
                    "execute('CREATE TABLE example (data TEXT)', ())",
                ),
                (
                    TEST_LOGGER.name,
                    DEBUG,
                    "execute('INSERT INTO example (data) VALUES (?)', ('one',))",
                ),
                (
                    TEST_LOGGER.name,
                    DEBUG,
                    "executemany('INSERT INTO example (data) VALUES (?)', (('two',),))",
                ),
                (
                    TEST_LOGGER.name,
                    DEBUG,
                    "executemany('INSERT INTO example (data) VALUES (?)', (('three',), ... 1 element omitted ...))",
                ),
                (
                    TEST_LOGGER.name,
                    DEBUG,
                    "executemany('INSERT INTO example (data) VALUES (?)', (('five',), ... 2 element(s) omitted ...))",
                ),
                (
                    TEST_LOGGER.name,
                    DEBUG,
                    "close()",
                ),
            ]
        finally:
            cursor.close()

        # to check that the cursor close above didn't close the connection
        assert is_open(conn)

    finally:
        conn.close()
