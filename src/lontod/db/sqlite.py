"""Implements Connections to an sqlite database"""

from dataclasses import dataclass, field
from enum import Enum

from sqlite3 import Connection, connect
from typing import Any


class SqliteMode(Enum):
    """Modes for connecting to an sqlite database"""

    READ_ONLY = "ro"
    READ_WRITE = "rw"
    READ_WRITE_CREATE = "rwc"
    MEMORY = "memory"


@dataclass
class SqliteConnector:
    """Represents connection parameter for an sqlite database"""

    filename: str
    mode: SqliteMode = SqliteMode.READ_WRITE_CREATE
    check_same_thread: bool = False
    kwargs: dict[str, Any] = field(default_factory=dict)

    @property
    def connect_url(self) -> str:
        return f"file:{self.filename}?mode={self.mode.value}"

    @property
    def connect_kwargs(self) -> dict[str, Any]:
        kwargs = self.kwargs.copy()
        kwargs["check_same_thread"] = self.check_same_thread
        return kwargs

    def connect(self) -> Connection:
        """Creates a connection to the given database"""
        conn = connect(self.connect_url, **self.connect_kwargs)  # type: Connection
        return conn
