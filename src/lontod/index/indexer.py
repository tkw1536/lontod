"""indexing functionality"""

from logging import Logger
from sqlite3 import Connection
from typing import Optional

from ..ontologies import Ontology
from ..sqlite import LoggingCursorContext

_TABLE_SCHEMA_ = """
CREATE TABLE IF NOT EXISTS "NAMES" (
    "SLUG"    TEXT NOT NULL PRIMARY KEY,
    "URI"   TEXT NOT NULL
) STRICT;
CREATE INDEX IF NOT EXISTS "INDEX_NAMES" ON "NAMES" ("URI");

CREATE TABLE IF NOT EXISTS "DEFINIENDA" (
    "URI"       TEXT NOT NULL,
    "ONTOLOGY"  TEXT NOT NULL,
    "FRAGMENT"  TEXT
) STRICT;
CREATE INDEX IF NOT EXISTS "INDEX_DEFINIENDA" ON "DEFINIENDA" ("URI");

CREATE TABLE IF NOT EXISTS "ONTOLOGIES" (
    "URI"        TEXT NOT NULL,
    "MIME_TYPE" TEXT NOT NULL,
    "DATA"      BLOB NOT NULL
) STRICT;
CREATE INDEX IF NOT EXISTS "INDEX_ONTOLOGIES" ON "ONTOLOGIES" ("URI", "MIME_TYPE");
"""


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
            cursor.execute("DELETE FROM ONTOLOGIES")
            cursor.execute("DELETE FROM NAMES")

    def remove(self, slug: Optional[str] = None, uri: Optional[str] = None) -> None:
        """Remove any indexed data from the database which match either the slug or the URI"""

        with self._cursor() as cursor:
            # delete by slug
            if slug is not None:
                cursor.execute(
                    "DELETE FROM DEFINIENDA WHERE ONTOLOGY IN (SELECT URI FROM NAMES WHERE SLUG = ?)",
                    (slug,),
                )
                cursor.execute(
                    "DELETE FROM ONTOLOGIES WHERE URI IN (SELECT URI FROM NAMES WHERE SLUG = ?)",
                    (slug,),
                )
                cursor.execute("DELETE FROM NAMES WHERE SLUG = ?", (slug,))

            # delete by uri
            if uri is not None:
                cursor.execute("DELETE FROM DEFINIENDA WHERE ONTOLOGY = ?", (uri,))
                cursor.execute("DELETE FROM ONTOLOGIES WHERE URI = ?", (uri,))
                cursor.execute("DELETE FROM NAMES WHERE URI = ?", (uri,))

    def upsert(self, slug: str, ontology: Ontology) -> None:
        """Inserts the given ontology into the database, removing any old references as necessary"""

        self.remove(slug, ontology.uri)

        with self._cursor() as cursor:
            cursor.execute(
                "INSERT INTO NAMES (SLUG, URI) VALUES (?, ?)", (slug, ontology.uri)
            )
            cursor.executemany(
                "INSERT INTO ONTOLOGIES (URI, MIME_TYPE, DATA) VALUES(?, ?, CAST(? AS BLOB))",
                [
                    (ontology.uri, media_type, data)
                    for (media_type, data) in ontology.encodings.items()
                ],
            )
            cursor.executemany(
                "INSERT INTO DEFINIENDA (URI, ONTOLOGY, FRAGMENT) VALUES(?, ?, ?)",
                [
                    (definiendum, ontology.uri, fragment)
                    for (definiendum, fragment) in ontology.definienda
                ],
            )
