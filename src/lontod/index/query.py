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

    def get_data(self, uri: str, mime_type: str) -> Optional[bytes]:
        """receives the encoding of the ontology with the given uri and mime_type"""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT ONTOLOGIES.DATA FROM ONTOLOGIES WHERE ONTOLOGIES.URI = ? AND ONTOLOGIES.MIME_TYPE = ? LIMIT 1",
                (uri, mime_type),
            )

            row = cursor.fetchone()
            if row is None:
                return None

            if not _is_row_blob(row):
                raise AssertionError("expected (BLOB)")

            return as_utf8(row[0])

    def get_definiendum(
        self, *uris: Iterable[str]
    ) -> Optional[Tuple[str, str, Optional[str]]]:
        """Returns the slug and fragment any of the given URIs are defined in"""

        # nothing requested, nothing returned!
        if len(uris) == 0:
            return None

        with self._cursor() as cursor:
            cursor.execute(
                "SELECT NAMES.SLUG, NAMES.URI, DEFINIENDA.FRAGMENT FROM DEFINIENDA INNER JOIN NAMES ON DEFINIENDA.ONTOLOGY = NAMES.URI WHERE DEFINIENDA.URI IN ("
                + ",".join(["?"] * len(uris))
                + ")  LIMIT 1",
                [str(u) for u in uris],
            )

            row = cursor.fetchone()
            if row is None:
                return None

            if not _is_row_text_text_ntext(row):
                print(row)
                raise AssertionError("expected (TEXT, TEXT, TEXT OR NULL)")

            return row

    def has_mime_type(self, uri: str, typ: str) -> bool:
        """checks if the ontology with the given uri exits as the given slug"""

        with self._cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM ONTOLOGIES WHERE ONTOLOGIES.URI = ? AND ONTOLOGIES.MIME_TYPE = ? LIMIT 1",
                (uri, typ),
            )

            row = cursor.fetchone()
            if row is None:
                return False
            if not _is_row_int(row):
                return False

            return row[0] == 1

    def get_mime_types(self, uri: str) -> set[str]:
        """Returns a set containing all available mime types representations for the given uri"""
        mime_types = set()

        with self._cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT ONTOLOGIES.MIME_TYPE FROM ONTOLOGIES WHERE ONTOLOGIES.URI = ?",
                (uri,),
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


def _is_row_int(value: Any) -> TypeGuard[Tuple[int]]:
    return isinstance(value, tuple) and len(value) == 1 and isinstance(value[0], int)


def _is_row_text_text_ntext(value: Any) -> TypeGuard[Tuple[str, str, Optional[str]]]:
    return (
        isinstance(value, tuple)
        and len(value) == 3
        and isinstance(value[0], str)
        and isinstance(value[1], str)
        and (value[2] is None or isinstance(value[2], str))
    )


# spellchecker:words ntext
