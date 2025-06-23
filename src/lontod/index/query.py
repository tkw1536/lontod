"""query functionality."""

import json
from collections.abc import Generator, Iterable
from dataclasses import dataclass
from logging import Logger
from sqlite3 import Connection
from typing import Any, TypeGuard, final

from lontod.sqlite import Connector, LoggingCursorContext
from lontod.utils.pool import Pool
from lontod.utils.strings import as_utf8


@final
@dataclass(frozen=True)
class Ontology:
    """an ontology as stored in the database."""

    identifier: str
    uri: str

    alternate_uris: list[str]
    mime_types: list[str]
    definienda_count: int


@final
@dataclass(frozen=True)
class Definiendum:
    """a definiendum result."""

    uri: str
    ontology_identifier: str
    canonical: bool
    fragment: str | None


@final
class Query:
    """functionality for interacting with indexed ontologies."""

    __conn: Connection
    __logger: Logger

    def __init__(self, conn: Connection, logger: Logger) -> None:
        """Create a new Query instance."""
        self.__conn = conn
        self.__logger = logger

    @property
    def conn(self) -> Connection:
        """Connection used by this query object."""
        return self.__conn

    def _cursor(self) -> LoggingCursorContext:
        return LoggingCursorContext(self.__conn, self.__logger)

    def list_ontologies(self) -> Generator[Ontology]:
        """List all (identifier, uri, list[types], len(definienda)) ontologies found in the database."""
        with self._cursor() as cursor:
            cursor.execute(
                """
SELECT
    ONTOLOGIES.ONTOLOGY_ID,
    ONTOLOGIES.URI,
    ONTOLOGIES.ALTERNATE_URIS,
    ONTOLOGIES.DEFINIENDA_COUNT,
    ONTOLOGIES.MIME_TYPES
FROM
    ONTOLOGIES
""",
            )

            while True:
                row = cursor.fetchone()
                if row is None:
                    return

                if not _is_row_text_text_text_int_text(row):
                    msg = "expected (TEXT,TEXT,TEXT,INT,TEXT)"
                    raise AssertionError(msg)

                alternate_uris = json.loads(row[2])
                if not _is_list_str(alternate_uris):
                    msg = "expected LIST[TEXT]"
                    raise AssertionError(msg)

                mime_types = json.loads(row[4])
                if not _is_list_str(mime_types):
                    msg = "expected LIST[TEXT]"
                    raise AssertionError(msg)

                yield Ontology(
                    identifier=row[0],
                    uri=row[1],
                    alternate_uris=alternate_uris,
                    mime_types=mime_types,
                    definienda_count=row[3],
                )

    def get_data(self, identifier: str, mime_type: str) -> bytes | None:
        """Receives the encoding of the ontology with the given slug and mime_type."""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT DATA.DATA FROM DATA WHERE DATA.ONTOLOGY_ID = ? AND DATA.MIME_TYPE = ? LIMIT 1",
                (identifier, mime_type),
            )

            row = cursor.fetchone()
            if row is None:
                return None

            if not _is_row_blob(row):
                msg = "expected (BLOB)"
                raise AssertionError(msg)

            return as_utf8(row[0])

    def get_definienda(
        self,
        *uris: Iterable[str],
    ) -> Generator[Definiendum]:
        """Return in any of the given uris."""
        # nothing requested, nothing returned!
        if len(uris) == 0:
            return

        with self._cursor() as cursor:
            cursor.execute(
                """
SELECT
	DEFINIENDA.URI,
	DEFINIENDA.ONTOLOGY_ID,
	DEFINIENDA.CANONICAL,
	DEFINIENDA.FRAGMENT
FROM
	DEFINIENDA
WHERE
	DEFINIENDA.URI IN ("""
                + ",".join(["?"] * len(uris))
                + """)
ORDER BY
	DEFINIENDA.CANONICAL DESC,
	DEFINIENDA.SORT_KEY DESC""",
                [str(u) for u in uris],
            )

            while True:
                row = cursor.fetchone()
                if row is None:
                    return

                if not _is_row_text_text_int_ntext(row):
                    msg = "expected (TEXT,TEXT,INTEGER,TEXT OR NULL)"
                    raise AssertionError(msg)

                yield Definiendum(
                    uri=row[0],
                    ontology_identifier=row[1],
                    canonical=row[2] == 1,
                    fragment=row[3],
                )

    def has_mime_type(self, identifier: str, typ: str) -> bool:
        """Check if the given ontology exists with the given identifier."""
        with self._cursor() as cursor:
            cursor.execute(
                """SELECT EXISTS (SELECT 1 FROM DATA WHERE DATA.MIME_TYPE = ? AND DATA.ONTOLOGY_ID = ?)""",
                (typ, identifier),
            )

            row = cursor.fetchone()
            if row is None:
                return False
            if not _is_row_int(row):
                return False

            return row[0] == 1

    def get_mime_types(self, identifier: str) -> Generator[str]:
        """Return a set containing all available mime types representations for the given mime_type."""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT DATA.MIME_TYPE FROM DATA WHERE DATA.ONTOLOGY_ID = ? ORDER BY DATA.MIME_TYPE",
                (identifier,),
            )

            for row in cursor.fetchall():
                if not _is_row_text(row):
                    msg = "expected (TEXT)"
                    raise AssertionError(msg)

                yield row[0]


class QueryPool(Pool[Query]):
    """Represents a pool of Query objects."""

    def __init__(self, max_size: int, logger: Logger, connector: Connector) -> None:
        """Create a new QueryPool."""
        super().__init__(
            size=max_size,
            setup=self.__setup,
            reset=None,
            teardown=self.__teardown,
        )
        self._connector = connector
        self._logger = logger

    def __setup(self) -> Query:
        self._logger.debug("establishing new database connection")
        conn = self._connector.connect()
        return Query(conn, self._logger)

    def __teardown(self, query: Query) -> None:
        self._logger.debug("closing database connection")
        query.conn.close()


def _is_row_text_text_text_int_text(
    value: Any,
) -> TypeGuard[tuple[str, str, str, int, str]]:
    return (
        isinstance(value, tuple)
        and len(value) == 5  # noqa: PLR2004
        and isinstance(value[0], str)
        and isinstance(value[1], str)
        and isinstance(value[2], str)
        and isinstance(value[3], int)
        and isinstance(value[4], str)
    )


def _is_list_str(value: Any) -> TypeGuard[list[str]]:
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


def _is_row_blob(value: Any) -> TypeGuard[tuple[bytes]]:
    return isinstance(value, tuple) and len(value) == 1 and isinstance(value[0], bytes)


def _is_row_text(value: Any) -> TypeGuard[tuple[str]]:
    return isinstance(value, tuple) and len(value) == 1 and isinstance(value[0], str)


def _is_row_int(value: Any) -> TypeGuard[tuple[int]]:
    return isinstance(value, tuple) and len(value) == 1 and isinstance(value[0], int)


def _is_row_text_text_int_ntext(
    value: Any,
) -> TypeGuard[tuple[str, str, int, str | None]]:
    return (
        isinstance(value, tuple)
        and len(value) == 4  # noqa: PLR2004
        and isinstance(value[0], str)
        and isinstance(value[1], str)
        and isinstance(value[2], int)
        and (value[3] is None or isinstance(value[3], str))
    )


# spellchecker:words ntext
