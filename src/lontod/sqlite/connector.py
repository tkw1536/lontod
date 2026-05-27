"""implements connections to an sqlite database."""

from dataclasses import dataclass
from enum import Enum
from sqlite3 import Connection, connect
from typing import Any, cast, final

from lontod.utils.frozendict import FrozenDict


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
    enable_locking_tweaks: bool = True
    timeout_seconds: float = 30.0
    kwargs: FrozenDict[str, Any] = FrozenDict()

    @property
    def connect_url(self) -> str:
        """URL used to connect to the database."""
        return f"file:{self.filename}?mode={self.mode.value}"

    @property
    def connect_kwargs(self) -> dict[str, Any]:
        """Kwargs used for connect call."""
        kwargs = dict(self.kwargs)
        kwargs["check_same_thread"] = self.check_same_thread
        return kwargs

    def connect(self) -> Connection:
        """Call connect with the given arguments."""
        connect_kwargs = self.connect_kwargs
        if self.enable_locking_tweaks and "timeout" not in connect_kwargs:
            connect_kwargs["timeout"] = self.timeout_seconds

        conn = connect(self.connect_url, **connect_kwargs)
        if self.enable_locking_tweaks:
            # sqlite PRAGMA statements don't support parameter binding
            conn.execute(f"PRAGMA busy_timeout = {int(self.timeout_seconds * 1000)};")
            if (
                self.mode in (Mode.READ_WRITE, Mode.READ_WRITE_CREATE)
                and self.filename != ""
            ):
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA synchronous = NORMAL;")
        return cast("Connection", conn)
