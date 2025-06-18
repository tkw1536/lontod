"""Implements Connections to an sqlite database"""

from collections.abc import Iterable, Sized
from logging import DEBUG, Logger
from sqlite3 import Connection, Cursor
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Optional,
    Self,
    Type,
    TypeAlias,
    final,
    override,
)

_Parameters: TypeAlias = Any
if TYPE_CHECKING:
    from sqlite3 import _Parameters


@final
class LoggingCursorContext:
    """A context that automatically closes a cursor and logs all output"""

    _cursor: "LoggingCursor"
    _conn: Connection
    _logger: Logger

    def __init__(self, conn: Connection, logger: Logger):
        self._conn = conn
        self._logger = logger

    def __enter__(self) -> "LoggingCursor":
        self._cursor = self._conn.cursor(
            factory=lambda conn: LoggingCursor(conn, self._logger)
        )
        return self._cursor

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Literal[False]:
        self._cursor.close()
        return False


@final
class LoggingCursor(Cursor):
    """a cursor function that logs all calls that execute sql code"""

    _logger: Logger
    _level: int

    def __init__(self, cursor: Connection, logger: Logger, level: int = DEBUG):
        super().__init__(cursor)
        self._logger = logger
        self._level = level

    @property
    def _should_log(self) -> bool:
        return self._logger.isEnabledFor(self._level)

    @override
    def execute(self, sql: str, parameters: _Parameters = (), /) -> Self:
        """execute a given sql statement"""
        if self._should_log:
            self._logger.log(
                self._level, f"execute({sql!r}, {self._repr_params(parameters)}"
            )
        super().execute(sql, parameters)
        return self

    @override
    def executemany(
        self, sql: str, seq_of_parameters: Iterable[_Parameters], /
    ) -> Self:
        """repeatedly execute an sql statement with the given params"""
        if self._should_log:
            first_param = "..."
            for p in seq_of_parameters:
                first_param = self._repr_params(p)
                break

            count = 0
            if isinstance(seq_of_parameters, Sized):
                count = len(seq_of_parameters)
            else:
                for p in seq_of_parameters:
                    count += 1

            self._logger.log(
                self._level,
                f"executemany({sql!r}) ({first_param}, ... {count - 1} element(s) omitted ...))",
            )
        super().executemany(sql, seq_of_parameters)
        return self

    def _repr_params(self, params: _Parameters) -> str:
        representation = repr(params)
        if len(representation) > 200:
            return f"(length {len(representation)} representation)"
        return representation

    @override
    def executescript(self, sql_script: str, /) -> Self:
        """execute an sql script"""
        if self._should_log:
            self._logger.log(self._level, f"executescript({sql_script!r})")
        super().executescript(sql_script)
        return self
