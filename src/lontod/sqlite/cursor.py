"""Implements Connections to an sqlite database."""

from collections.abc import Iterable, Sized
from logging import DEBUG, Logger
from sqlite3 import Connection, Cursor
from types import TracebackType
from typing import (
    Any,
    Final,
    Literal,
    Self,
    final,
    override,
)

type _Parameters = Any


@final
class LoggingCursorContext:
    """A context that automatically closes a cursor and logs all output."""

    _cursor: "LoggingCursor"
    _conn: Connection
    _logger: Logger

    def __init__(self, conn: Connection, logger: Logger) -> None:
        """Create a new LoggingCursorContext a connection and logger."""
        self._conn = conn
        self._logger = logger

    def __enter__(self) -> "LoggingCursor":
        """Open a new cursor that logs."""
        self._cursor = self._conn.cursor(
            factory=lambda conn: LoggingCursor(conn, self._logger),
        )
        return self._cursor

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        """Close the created cursor."""
        self._cursor.close()
        return False


@final
class LoggingCursor(Cursor):
    """a cursor function that logs all calls that execute sql code."""

    _logger: Logger
    _level: int

    def __init__(self, cursor: Connection, logger: Logger, level: int = DEBUG) -> None:
        """Create a new LoggingCursor."""
        super().__init__(cursor)
        self._logger = logger
        self._level = level

    @property
    def _should_log(self) -> bool:
        return self._logger.isEnabledFor(self._level)

    @override
    def execute(self, sql: str, parameters: _Parameters = (), /) -> Self:
        """Execute a given sql statement."""
        if self._should_log:
            self._logger.log(
                self._level, "execute(%r, %s)", sql, self._repr_params(parameters)
            )
        super().execute(sql, parameters)
        return self

    @override
    def executemany(
        self,
        sql: str,
        seq_of_parameters: Iterable[_Parameters],
        /,
    ) -> Self:
        """Repeatedly execute an sql statement with the given params."""
        if self._should_log:
            first_param = "..."
            for p in seq_of_parameters:
                first_param = self._repr_params(p)
                break

            count = 0
            if isinstance(seq_of_parameters, Sized):
                count = len(seq_of_parameters)
            else:
                for _ in seq_of_parameters:
                    count += 1

            self._logger.log(
                self._level,
                "executemany(%r, (%s, ... %d element(s) omitted ...))",
                sql,
                first_param,
                count - 1,
            )
        super().executemany(sql, seq_of_parameters)
        return self

    MAX_REPR_PARAM_LENGTH: Final = 200

    def _repr_params(self, params: _Parameters) -> str:
        representation = repr(params)
        if len(representation) > LoggingCursor.MAX_REPR_PARAM_LENGTH:
            return f"(length {len(representation)} representation)"
        return representation

    @override
    def executescript(self, sql_script: str, /) -> Self:
        """Execute an sql script."""
        if self._should_log:
            self._logger.log(self._level, "executescript(%r)", sql_script)
        super().executescript(sql_script)
        return self
