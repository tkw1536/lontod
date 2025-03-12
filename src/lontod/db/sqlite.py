"""Implements Connections to an sqlite database"""

from dataclasses import dataclass

from sqlite3 import Connection, connect
from typing import Any, Tuple


@dataclass
class SqliteConnector:
    """Represents connection parameter for an sqlite database"""

    filename: str
    memory: bool = False
    readonly: bool = False
    check_same_thread: bool = False
    kwargs: dict[str, Any] = {}

    def connect_args(self) -> Tuple[str, dict[str, Any]]:
        """Returns arguments to be passed to connect"""

        url = f"file:{self.filename}?mode={'ro' if self.readonly else 'rw'}{"&mode=memory" if self.memory else ""}"

        kwargs = self.kwargs.copy()
        kwargs["check_same_thread"] = self.check_same_thread

        return url, kwargs

    def connect(self) -> Connection:
        """Creates a connection to the given database"""
        url, kwargs = self.connect_args()
        conn = connect(url, **kwargs)  # type: Connection
        return conn
