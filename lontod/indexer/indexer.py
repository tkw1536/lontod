from sqlite3 import Connection
from typing import Optional
from ..ontologies import Ontology

_TABLE_SCHEMA_ = """
CREATE TABLE IF NOT EXISTS "NAMES" (
    "SLUG"    TEXT NOT NULL PRIMARY KEY,
    "URI"   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS "INDEX_NAMES" ON "NAMES" ("ID");

CREATE TABLE IF NOT EXISTS "DEFINIENDA" (
    "URI"       TEXT NOT NULL PRIMARY KEY,
    "ONTOLOGY"  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS "INDEX_DEFINIENDA" ON "DEFINIENDA" ("URI");

CREATE TABLE IF NOT EXISTS "ONTOLOGIES" (
    "URI"        TEXT NOT NULL,
    "MIME_TYPE" TEXT NOT NULL,
    "DATA"      BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS "INDEX_ONTOLOGIES" ON "ONTOLOGIES" ("URI", "MIME_TYPE");
"""

class Indexer:
    """
        Implements indexing functionality.
    """

    conn: Connection
    
    def __init__(self, conn: Connection):
        self.conn = conn
    
    def initialize_schema(self):
        """
            Initializes the database schema, unless if already exists.
            Automatically commits any pending changes.
        """
        self.conn.executescript(_TABLE_SCHEMA_)
        self.conn.commit()

    def truncate(self):
        """ Removes all indexed data from the database """

        cursor = self.conn.cursor()
        try:
            cursor.execute("DELETE FROM DEFINIENDA")
            cursor.execute("DELETE FROM ONTOLOGIES")
            cursor.execute("DELETE FROM NAMES")
        finally:
            cursor.close()

    def remove(self, slug: Optional[str] = None, uri: Optional[str] = None):
        """ Remove any indexed data from the database which match either the slug or the URI """

        cursor = self.conn.cursor()
        try:
            # delete by slug
            if slug is not None:
                cursor.execute("DELETE FROM DEFINIENDA WHERE ONTOLOGY IN (SELECT URI FROM NAMES WHERE SLUG = ?)", (slug,))
                cursor.execute("DELETE FROM ONTOLOGIES WHERE URI IN (SELECT URI FROM NAMES WHERE SLUG = ?)", (slug,))
                cursor.execute("DELETE FROM NAMES WHERE SLUG = ?", (slug,))

            # delete by uri
            if uri is not None:
                cursor.execute("DELETE FROM DEFINIENDA WHERE ONTOLOGY = ?", (uri,))
                cursor.execute("DELETE FROM ONTOLOGIES WHERE URI = ?", (uri,))
                cursor.execute("DELETE FROM NAMES WHERE URI = ?", (uri,))
        finally:    
            cursor.close()
    
    def upsert(self, slug: str, ontology: Ontology):
        """ Inserts the given ontology into the database, removing any old references as necessary"""

        self.remove(slug, ontology.uri)

        cursor = self.conn.cursor()
        try:
            cursor.execute('INSERT INTO NAMES (SLUG, URI) VALUES (?, ?)', (slug, ontology.uri))
            cursor.executemany(
                'INSERT INTO ONTOLOGIES (URI, MIME_TYPE, DATA) VALUES(?, ?, ?)',
                [
                    (ontology.uri,media_type,data) for (media_type, data) in ontology.encodings.items()
                ]
            )
            cursor.executemany(
                'INSERT INTO DEFINIENDA (URI, ONTOLOGY) VALUES(?, ?)',
                [
                    (definiendum, ontology.uri) for definiendum in ontology.definienda
                ]
            )
        finally:
            cursor.close()
