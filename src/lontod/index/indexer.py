"""indexing functionality."""

from logging import Logger
from sqlite3 import Connection
from typing import Final, final

from lontod.ontologies import Ontology
from lontod.sqlite import LoggingCursorContext

_TABLE_SCHEMA_: Final[str] = """
CREATE TABLE IF NOT EXISTS "DEFINIENDA" (
    "URI"           TEXT NOT NULL,
    "ONTOLOGY_ID"   TEXT NOT NULL,
    "SORT_KEY"      TEXT NOT NULL,
    "CANONICAL"     INTEGER NOT NULL,
    "FRAGMENT"      TEXT
);

CREATE INDEX IF NOT EXISTS DEFINIENDA_ONTOLOGY ON DEFINIENDA ("ONTOLOGY_ID", "FRAGMENT", "SORT_KEY");
CREATE INDEX IF NOT EXISTS DEFINIENDA_FRAGMENT ON DEFINIENDA ("FRAGMENT");

CREATE TABLE IF NOT EXISTS "DATA" (
    "ONTOLOGY_ID"   TEXT NOT NULL,
    "MIME_TYPE"     TEXT NOT NULL,
    "DATA"          BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS "INDEX_DATA" ON "DATA" ("ONTOLOGY_ID", "MIME_TYPE");

DROP VIEW IF EXISTS "ONTOLOGIES";
CREATE VIEW IF NOT EXISTS
    "ONTOLOGIES"
AS SELECT
  NAMES.ONTOLOGY_ID,
  NAMES.URI,
  (
    SELECT
        JSON_GROUP_ARRAY(DEFINIENDA.URI)
    FROM
        DEFINIENDA
    WHERE
        DEFINIENDA.ONTOLOGY_ID = NAMES.ONTOLOGY_ID
        AND DEFINIENDA.CANONICAL IS FALSE
        AND DEFINIENDA.FRAGMENT IS NULL
    ORDER BY DEFINIENDA.URI
  ) AS ALTERNATE_URIS,
  (
    SELECT
        COUNT(*)
    FROM
        DEFINIENDA
    WHERE
        DEFINIENDA.CANONICAL IS TRUE
        AND DEFINIENDA.ONTOLOGY_ID = NAMES.ONTOLOGY_ID
  ) AS DEFINIENDA_COUNT,
  (
    SELECT
        JSON_GROUP_ARRAY(DATA.MIME_TYPE)
        FROM
            DATA
        WHERE
            DATA.ONTOLOGY_ID = NAMES.ONTOLOGY_ID
        ORDER BY
            DATA.MIME_TYPE
  ) AS MIME_TYPES
FROM
  DEFINIENDA AS NAMES
WHERE
    NAMES.FRAGMENT IS NULL
    AND NAMES.CANONICAL IS TRUE
ORDER BY
    NAMES.SORT_KEY DESC
"""

# Re-do the indexes once the queries are finished!
#
# CREATE INDEX IF NOT EXISTS "INDEX_NAMES" ON "DEFINIENDA" ("ID", "CANONICAL", "URI");


@final
class Indexer:
    """Low-level database-interacting indexing functionality."""

    conn: Connection
    _logger: Logger

    def __init__(self, conn: Connection, logger: Logger) -> None:
        """Create a new indexer."""
        self.conn = conn
        self._logger = logger

    def _cursor(self) -> LoggingCursorContext:
        return LoggingCursorContext(self.conn, self._logger)

    def initialize_schema(self) -> None:
        """Initialize the database schema.

        If the database schema already exists, does nothing.
        Automatically commits any pending changes.
        """
        with self._cursor() as cursor:
            cursor.executescript(_TABLE_SCHEMA_)

    def truncate(self) -> None:
        """Remove all indexed data from the database."""
        with self._cursor() as cursor:
            cursor.execute("DELETE FROM DEFINIENDA")
            cursor.execute("DELETE FROM DATA")

    def remove(self, identifier: str) -> None:
        """Remove any indexed data from the database with the given identifier."""
        with self._cursor() as cursor:
            cursor.execute(
                "DELETE FROM DEFINIENDA WHERE ONTOLOGY_ID = ?",
                (identifier,),
            )
            cursor.execute(
                "DELETE FROM DATA WHERE ONTOLOGY_ID = ?",
                (identifier,),
            )

    def upsert(
        self,
        identifier: str,
        ontology: Ontology,
        sort_key: str | None = None,
    ) -> None:
        """Insert the given ontology into the database, removing any old references to it."""
        self.remove(identifier)
        sort_key = sort_key if isinstance(sort_key, str) else identifier

        with self._cursor() as cursor:
            cursor.executemany(
                "INSERT INTO DEFINIENDA (URI, ONTOLOGY_ID, CANONICAL, FRAGMENT, SORT_KEY) VALUES (?, ?, ?, NULL, ?)",
                [
                    (uri, identifier, canonical, sort_key)
                    for (uri, canonical) in ontology.uris
                ],
            )
            cursor.executemany(
                "INSERT INTO DATA (ONTOLOGY_ID, MIME_TYPE, DATA) VALUES(?, ?, CAST(? AS BLOB))",
                [
                    (identifier, media_type, data)
                    for (media_type, data) in ontology.encodings.items()
                ],
            )
            cursor.executemany(
                "INSERT INTO DEFINIENDA (URI, ONTOLOGY_ID, CANONICAL, FRAGMENT, SORT_KEY) VALUES(?, ?, ?, ?, ?)",
                [
                    (definiendum, identifier, canonical, fragment, sort_key)
                    for (definiendum, fragment, canonical) in ontology.all_definienda
                ],
            )
