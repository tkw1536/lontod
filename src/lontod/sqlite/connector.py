"""implements connections to an sqlite database."""

from dataclasses import dataclass, field
from enum import Enum
from sqlite3 import Connection, connect
from typing import Any, cast, final


@final
class Mode(Enum):
    """Modes for connecting to an sqlite database."""

    READ_ONLY = "ro"
    READ_WRITE = "rw"
    READ_WRITE_CREATE = "rwc"
    MEMORY = "memory"
    MEMORY_SHARED_CACHE = "memory&cache=shared"


@final
@dataclass(frozen=True)
class Connector:
    """Represents connection parameter for an sqlite database."""

    filename: str
    mode: Mode = Mode.READ_WRITE_CREATE
    check_same_thread: bool = False
    kwargs: dict[str, Any] = field(default_factory=dict)

    @property
    def connect_url(self) -> str:
        """URL used to connect to the database."""
        return f"file:{self.filename}?mode={self.mode.value}"

    @property
    def connect_kwargs(self) -> dict[str, Any]:
        """Kwargs used for connect call."""
        kwargs = self.kwargs.copy()
        kwargs["check_same_thread"] = self.check_same_thread
        return kwargs

    def connect(self) -> Connection:
        """Call connect with the given arguments."""
        conn = connect(self.connect_url, **self.connect_kwargs)
        return cast("Connection", conn)
