"""implements a watcher for indexing"""

from logging import Logger
from sqlite3 import Connection
from threading import Lock
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from ..utils.debounce import debounce
from .indexer import Indexer
from .ingester import Ingester


class Watcher:
    """Watches a file or directory for changes and re-indexes when needed"""

    conn: Connection
    observer: BaseObserver | None = None
    path: str
    logger: Logger
    html_languages: list[str]

    def __init__(
        self, conn: Connection, path: str, html_languages: list[str], logger: Logger
    ):
        self.conn = conn
        self.logger = logger
        self.path = path
        self.html_languages = html_languages

    def start(self) -> None:
        """starts watching the given directory"""

        if self.observer is not None:
            raise AssertionError("observer already started")

        self.logger.info("initializing database")
        indexer = Indexer(self.conn, self.logger)
        indexer.initialize_schema()

        ingester = Ingester(indexer, self.html_languages, self.logger)

        self.logger.info(f"performing initial index of {self.path!r}")
        handler = ReIndexingHandler(indexer, ingester, self.path, self.logger)
        handler.reindex_now(force=True)

        self.logger.info(f"starting to watch {self.path!r}")
        self.observer = Observer()
        self.observer.schedule(handler, self.path, recursive=True)
        self.observer.start()

    def close(self) -> None:
        """closes the observer and the connection"""
        self.conn.close()

        if self.observer is not None:
            self.logger.info(f"stopping watch of {self.path!r}")
            self.observer.stop()


class ReIndexingHandler(FileSystemEventHandler):
    """triggers re-indexing"""

    logger: Logger
    lock: Lock
    ingester: Ingester
    indexer: Indexer
    debounce_seconds: float
    path: str
    reindex: Callable[[], None]

    def __init__(
        self,
        indexer: Indexer,
        ingester: Ingester,
        path: str,
        logger: Logger,
        debounce_seconds: float = 1.0,
    ):
        self.indexer = indexer
        self.ingester = ingester
        self.logger = logger
        self.lock = Lock()
        self.path = path
        self.debounce_seconds = debounce_seconds
        self.reindex = debounce(debounce_seconds)(self.reindex_now)

    def on_any_event(self, event: FileSystemEvent) -> None:
        """called when any event occurs"""
        self.reindex()

    def reindex_now(self, force: bool = False) -> None:
        """triggers a reindexing procedure, and logs in case of failure"""

        with self.lock:
            self.indexer.conn.execute("BEGIN;")

            ok = True
            try:
                self._reindex()
            except Exception as e:
                self.logger.error(f"failed to ingest: {e}")
                ok = False

            if ok or force:
                self.logger.info("committing indexed ontologies")
                self.indexer.conn.commit()
            else:
                self.logger.error("rolling back indexed ontologies")
                self.indexer.conn.rollback()

    def _reindex(self) -> None:
        self.indexer.truncate()

        failures: list[str] = []
        try:
            _, failures = self.ingester.ingest(self.path)
        except AssertionError as err:
            self.logger.error("unable to ingest %r: %s", self.path, err)

        if len(failures) > 0:
            raise AssertionError(
                f"failed to ingest {",".join([repr(f) for f in failures])}"
            )
