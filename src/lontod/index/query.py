"""query functionality"""

from logging import Logger
from sqlite3 import Connection
from typing import Any, Iterable, Optional, Tuple, TypeGuard, final

from ..sqlite import Connector, LoggingCursorContext
from ..utils.pool import Pool
from ..utils.strings import as_utf8


@final
class Query:
    """functionality for interacting with indexed ontologies"""

    __conn: Connection
    __logger: Logger

    def __init__(self, conn: Connection, logger: Logger):
        """Creates a new Query instance"""
        self.__conn = conn
        self.__logger = logger

    @property
    def conn(self) -> Connection:
        """connection used by this query object"""
        return self.__conn

    def _cursor(self) -> LoggingCursorContext:
        return LoggingCursorContext(self.__conn, self.__logger)

    def list_ontologies(self) -> Iterable[Tuple[str, str]]:
        """Lists all (slug, name) ontologies found in the database"""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT NAMES.SLUG, NAMES.URI FROM NAMES ORDER BY NAMES.SLUG"
            )
            while True:
                row = cursor.fetchone()
                if row is None:
                    return
                if not _is_row_text_text(row):
                    raise AssertionError("expected (TEXT,TEXT)")

                yield row[0], row[1]

    def get_data(self, slug: str, mime_type: str) -> Optional[bytes]:
        """receives the encoding of the ontology with the given slug and mime_type"""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT ONTOLOGIES.DATA FROM ONTOLOGIES INNER JOIN NAMES ON ONTOLOGIES.URI = NAMES.URI WHERE NAMES.SLUG = ? AND ONTOLOGIES.MIME_TYPE = ? LIMIT 1",
                (slug, mime_type),
            )

            row = cursor.fetchone()
            if row is None:
                return None

            if not _is_row_blob(row):
                raise AssertionError("expected (BLOB)")

            return as_utf8(row[0])

    def get_definiendum(
        self, *uris: Iterable[str]
    ) -> Optional[Tuple[str, Optional[str]]]:
        """Returns the slug and fragment any of the given URIs are defined in"""

        # nothing requested, nothing returned!
        if len(uris) == 0:
            return None

        with self._cursor() as cursor:
            cursor.execute(
                "SELECT NAMES.SLUG, DEFINIENDA.FRAGMENT FROM DEFINIENDA INNER JOIN NAMES ON DEFINIENDA.ONTOLOGY = NAMES.URI WHERE DEFINIENDA.URI IN ("
                + ",".join(["?"] * len(uris))
                + ")  LIMIT 1",
                [str(u) for u in uris],
            )

            row = cursor.fetchone()
            if row is None:
                return None

            if not _is_row_text_ntext(row):
                raise AssertionError("expected (TEXT, TEXT OR NULL)")

            return row

    def get_mime_types(self, slug: str) -> set[str]:
        """Returns a set containing all available mime types representations for the given slug"""
        mime_types = set()

        with self._cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT ONTOLOGIES.MIME_TYPE FROM ONTOLOGIES INNER JOIN NAMES ON ONTOLOGIES.URI = NAMES.URI WHERE NAMES.SLUG = ?",
                (slug,),
            )

            for row in cursor.fetchall():
                if not _is_row_text(row):
                    raise AssertionError("expected (TEXT)")
                mime_types.add(row[0])

        return mime_types


class QueryPool(Pool[Query]):
    """Represents a pool of Query objects"""

    def __init__(self, max_size: int, logger: Logger, connector: Connector):
        super().__init__(
            size=max_size, setup=self.__setup, reset=None, teardown=self.__teardown
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


def _is_row_text_text(value: Any) -> TypeGuard[Tuple[str, str]]:
    return (
        isinstance(value, tuple)
        and len(value) == 2
        and isinstance(value[0], str)
        and isinstance(value[1], str)
    )


def _is_row_blob(value: Any) -> TypeGuard[Tuple[bytes]]:
    return isinstance(value, tuple) and len(value) == 1 and isinstance(value[0], bytes)


def _is_row_text(value: Any) -> TypeGuard[Tuple[str]]:
    return isinstance(value, tuple) and len(value) == 1 and isinstance(value[0], str)


def _is_row_text_ntext(value: Any) -> TypeGuard[Tuple[str, Optional[str]]]:
    return (
        isinstance(value, tuple)
        and len(value) == 2
        and isinstance(value[0], str)
        and (value[1] is None or isinstance(value[1], str))
    )


# spellchecker:words ntext
