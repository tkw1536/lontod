from logging import Logger
from sqlite3 import Connection
from typing import Any, Iterable, List, Optional, Tuple

from ..db import Pool, SqliteConnector


class Query:
    """Query holds all functionality for querying data from a given connection"""

    conn: Connection

    def __init__(self, conn: Connection):
        """Creates a new Query instance"""
        self.conn = conn

    def list_ontologies(self) -> Iterable[Tuple[str, str]]:
        """Lists all (slug, name) ontologies found in the database"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "SELECT NAMES.SLUG, NAMES.URI FROM NAMES ORDER BY NAMES.SLUG"
            )
            while True:
                row = cursor.fetchone()
                if row is None:
                    return
                (slug, uri) = row
                yield (str(slug), str(uri))
        finally:
            cursor.close()

    def get_data(self, slug: str, mime_type: str) -> Optional[bytes]:
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "SELECT ONTOLOGIES.DATA FROM ONTOLOGIES INNER JOIN NAMES ON ONTOLOGIES.URI = NAMES.URI WHERE NAMES.SLUG = ? AND ONTOLOGIES.MIME_TYPE = ? LIMIT 1",
                (slug, mime_type),
            )

            (data,) = cursor.fetchone()
            if isinstance(data, str):
                return data.encode("utf-8")
            elif isinstance(data, bytes):
                return data
            else:
                return None  # not sure what this is
        except Exception:
            return None
        finally:
            cursor.close()

    def get_mime_types_uri(self, uri: str) -> set[str]:
        return self._get_mime_types(
            "SELECT DISTINCT ONTOLOGIES.MIME_TYPE FROM ONTOLOGIES WHERE ONTOLOGIES.URI = ?",
            (uri,),
        )

    def get_mime_types_slug(self, slug: str) -> set[str]:
        return self._get_mime_types(
            "SELECT DISTINCT ONTOLOGIES.MIME_TYPE FROM ONTOLOGIES INNER JOIN NAMES ON ONTOLOGIES.URI = NAMES.URI WHERE NAMES.SLUG = ?",
            (slug,),
        )

    def get_definiendum(self, *uris: List[str]) -> Optional[Tuple[str, Optional[str]]]:
        """Returns the slug and fragment any of the given URIs are defined in"""

        # nothing requested, nothing returned!
        if len(uris) == 0:
            return None

        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "SELECT NAMES.SLUG, DEFINIENDA.FRAGMENT FROM DEFINIENDA INNER JOIN NAMES ON DEFINIENDA.ONTOLOGY = NAMES.URI WHERE DEFINIENDA.URI IN ("
                + ",".join(["?"] * len(uris))
                + ")  LIMIT 1",
                [str(u) for u in uris],
            )

            result = cursor.fetchone()
            if result is None:
                return None

            slug, fragment = result
            return str(slug), (str(fragment) if fragment is not None else None)
        finally:
            cursor.close()

    def _get_mime_types(self, query: str, params: Iterable[Any]) -> set[str]:
        mime_types = set()

        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)

            for (mime_type,) in cursor.fetchall():
                mime_types.add(str(mime_type))
        finally:
            cursor.close()

        return mime_types


class QueryPool(Pool[Query]):
    """Represents a pool of Query objects"""

    def __init__(self, max_size: int, logger: Logger, connector: SqliteConnector):
        super().__init__(size=max_size, setup=self.__setup, teardown=self.__teardown)
        self._connector = connector
        self._logger = logger

    def __setup(self) -> Query:
        self._logger.debug("establishing new database connection")
        conn = self._connector.connect()
        return Query(conn)

    def __teardown(self, query: Query) -> None:
        self._logger.debug("closing database connection")
        query.conn.close()
