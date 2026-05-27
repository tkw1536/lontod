"""Test the connector module."""

from pathlib import Path
from typing import Any

import pytest

from lontod.sqlite.check import is_open
from lontod.sqlite.connector import Connector, Mode


@pytest.mark.parametrize(
    ("connector", "want_url", "want_connect_kwargs"),
    [
        (
            Connector("example", mode=Mode.READ_ONLY),
            "file:example?mode=ro",
            {"check_same_thread": False},
        ),
        (
            Connector("example", mode=Mode.READ_WRITE),
            "file:example?mode=rw",
            {"check_same_thread": False},
        ),
        (
            Connector("example", mode=Mode.READ_WRITE_CREATE),
            "file:example?mode=rwc",
            {"check_same_thread": False},
        ),
        (
            Connector("", mode=Mode.MEMORY),
            "file:?mode=memory",
            {"check_same_thread": False},
        ),
        (
            Connector("", mode=Mode.MEMORY_SHARED_CACHE),
            "file:?mode=memory&cache=shared",
            {"check_same_thread": False},
        ),
        (
            Connector("something", mode=Mode.READ_WRITE, check_same_thread=True),
            "file:something?mode=rw",
            {"check_same_thread": True},
        ),
    ],
)
def test_connector_params(
    connector: Connector, want_url: str, want_connect_kwargs: dict[str, Any]
) -> None:
    """Tests the Connector class."""
    assert connector.connect_url == want_url
    assert connector.connect_kwargs == want_connect_kwargs


def test_connector_connect() -> None:
    """Tests that the connector connect function creates fresh connections."""
    connector = Connector("", mode=Mode.MEMORY)

    conn1 = connector.connect()
    try:
        assert is_open(conn1)

        conn2 = connector.connect()
        try:
            assert is_open(conn2)

            assert conn1 is not conn2
            conn1.close()
            assert not is_open(conn1)
            assert is_open(conn2)

        finally:
            conn2.close()
    finally:
        conn1.close()


def test_connector_locking_tweaks_toggle(tmp_path: Path) -> None:
    """Tests that locking tweaks can be toggled."""
    db = tmp_path / "lontod-test.sqlite"

    enabled = Connector(
        str(db),
        mode=Mode.READ_WRITE_CREATE,
        enable_locking_tweaks=True,
        timeout_seconds=0.1,
    )
    conn1 = enabled.connect()
    try:
        want_busy = int(0.1 * 1000)
        got_busy = conn1.execute("PRAGMA busy_timeout;").fetchone()
        assert got_busy == (want_busy,)

        got_journal = conn1.execute("PRAGMA journal_mode;").fetchone()
        assert got_journal == ("wal",)
    finally:
        conn1.close()

    db2 = tmp_path / "lontod-test2.sqlite"
    disabled = Connector(
        str(db2),
        mode=Mode.READ_WRITE_CREATE,
        enable_locking_tweaks=False,
    )
    conn2 = disabled.connect()
    try:
        got_journal2 = conn2.execute("PRAGMA journal_mode;").fetchone()
        assert got_journal2 != ("wal",)
    finally:
        conn2.close()
