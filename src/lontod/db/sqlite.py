from sqlite3 import Connection, connect


class SqliteConnector:
    """Represents a connection to an sqlite database"""

    def __init__(
        self, filename: str, readonly: bool = False, check_same_thread=False, **kwargs
    ):
        self._url = f"file:{filename}?mode={'ro' if readonly else 'rw'}"
        self._kwargs = kwargs
        self._kwargs["check_same_thread"] = check_same_thread

    def connect(self) -> Connection:
        return connect(self._url, **self._kwargs)
