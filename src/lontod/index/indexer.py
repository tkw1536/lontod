"""indexing functionality"""

from logging import Logger
from sqlite3 import Connection
from typing import final

from ..ontologies import Ontology
from ..sqlite import LoggingCursorContext

_TABLE_SCHEMA_ = """
CREATE TABLE IF NOT EXISTS "DEFINIENDA" (
    "URI"           TEXT NOT NULL,
    "ONTOLOGY_ID"   TEXT NOT NULL,
    "CANONICAL"     INTEGER NOT NULL,
    "FRAGMENT"      TEXT
);

CREATE INDEX IF NOT EXISTS DEFINIENDA_ONTOLOGY ON DEFINIENDA ("ONTOLOGY_ID", "FRAGMENT");
CREATE INDEX IF NOT EXISTS DEFINIENDA_FRAGMENT ON DEFINIENDA("FRAGMENT");

CREATE TABLE IF NOT EXISTS "DATA" (
    "ONTOLOGY_ID"   TEXT NOT NULL,
    "MIME_TYPE"     TEXT NOT NULL,
    "DATA"          BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS "INDEX_DATA" ON "DATA" ("ONTOLOGY_ID", "MIME_TYPE");
"""

# Re-do the indexes once the queries are finished!
#
# CREATE INDEX IF NOT EXISTS "INDEX_NAMES" ON "DEFINIENDA" ("ID", "CANONICAL", "URI");


@final
class Indexer:
    """Low-level database-interacting indexing functionality"""

    conn: Connection
    _logger: Logger

    def __init__(self, conn: Connection, logger: Logger):
        self.conn = conn
        self._logger = logger

    def _cursor(self) -> LoggingCursorContext:
        return LoggingCursorContext(self.conn, self._logger)

    def initialize_schema(self) -> None:
        """
        Initializes the database schema, unless if already exists.
        Automatically commits any pending changes.
        """
        with self._cursor() as cursor:
            cursor.executescript(_TABLE_SCHEMA_)

    def truncate(self) -> None:
        """Removes all indexed data from the database"""

        with self._cursor() as cursor:
            cursor.execute("DELETE FROM DEFINIENDA")
            cursor.execute("DELETE FROM DATA")

    def remove(self, identifier: str) -> None:
        """Remove any indexed data from the database with the given identifier"""

        with self._cursor() as cursor:
            cursor.execute(
                "DELETE FROM DEFINIENDA WHERE ONTOLOGY_ID = ?",
                (identifier,),
            )
            cursor.execute(
                "DELETE FROM DATA WHERE ONTOLOGY_ID = ?",
                (identifier,),
            )

    def upsert(self, identifier: str, ontology: Ontology) -> None:
        """Inserts the given ontology into the database, removing any old references to it"""

        self.remove(identifier)

        with self._cursor() as cursor:
            cursor.executemany(
                "INSERT INTO DEFINIENDA (URI, ONTOLOGY_ID, CANONICAL, FRAGMENT) VALUES (?, ?, ?, NULL)",
                [(uri, identifier, canonical) for (uri, canonical) in ontology.uris],
            )
            cursor.executemany(
                "INSERT INTO DATA (ONTOLOGY_ID, MIME_TYPE, DATA) VALUES(?, ?, CAST(? AS BLOB))",
                [
                    (identifier, media_type, data)
                    for (media_type, data) in ontology.encodings.items()
                ],
            )
            cursor.executemany(
                "INSERT INTO DEFINIENDA (URI, ONTOLOGY_ID, CANONICAL, FRAGMENT) VALUES(?, ?, ?, ?)",
                [
                    (definiendum, identifier, canonical, fragment)
                    for (definiendum, fragment, canonical) in ontology.all_definienda
                ],
            )
