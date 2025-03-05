from sqlite3 import Connection
from typing import Optional

class Query:
    def __init__(self, conn: Connection):
        self.conn = conn

    def get_data(self, slug: str, mime_type: str) -> Optional[bytes]:
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT ONTOLOGIES.DATA FROM ONTOLOGIES INNER JOIN NAMES ON ONTOLOGIES.URI = NAMES.URI WHERE NAMES.SLUG = ? AND ONTOLOGIES.MIME_TYPE = ? LIMIT 1", (slug, mime_type))

            (data,) = cursor.fetchone()
            if isinstance(data, str):
                return data.encode('utf-8')
            elif isinstance(data, bytes):
                return data
            else:
                return None # not sure what this is 
        except Exception as e:
            return None
        finally:
            cursor.close()

    def get_mime_types(self, slug: str) -> set[str]:
        mime_types = set()

        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT DISTINCT ONTOLOGIES.MIME_TYPE FROM ONTOLOGIES INNER JOIN NAMES ON ONTOLOGIES.URI = NAMES.URI WHERE SLUG = ?", (slug,))

            for (mime_type,) in cursor.fetchall():
                mime_types.add(str(mime_type))
        finally:
            cursor.close()
        
        return mime_types
