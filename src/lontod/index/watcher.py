"""implements a watcher for indexing"""

from logging import Logger
from sqlite3 import Connection
from threading import Lock
from typing import Callable, final

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from ..utils.debounce import debounce
from .indexer import Indexer
from .ingester import Ingester


@final
class Watcher:
    """Watches a file or directory for changes and re-indexes when needed"""

    __conn: Connection
    __observer: BaseObserver | None = None
    __path: str
    __logger: Logger
    __html_languages: list[str]

    def __init__(
        self, conn: Connection, path: str, html_languages: list[str], logger: Logger
    ):
        self.__conn = conn
        self.__logger = logger
        self.__path = path
        self.__html_languages = html_languages

    def start(self) -> None:
        """starts watching the given directory"""

        if self.__observer is not None:
            raise AssertionError("observer already started")

        ingester = Ingester(
            Indexer(self.__conn, self.__logger), self.__html_languages, self.__logger
        )

        self.__logger.info(f"performing initial index of {self.__path!r}")
        handler = ReIndexingHandler(ingester, self.__path, self.__logger)
        handler.reindex_now(initialize=True, force=True)

        self.__logger.info(f"starting to watch {self.__path!r}")
        self.__observer = Observer()
        self.__observer.schedule(handler, self.__path, recursive=True)
        self.__observer.start()

    def close(self) -> None:
        """closes the observer and the connection"""
        self.__conn.close()

        if self.__observer is not None:
            self.__logger.info(f"stopping watch of {self.__path!r}")
            self.__observer.stop()


@final
class ReIndexingHandler(FileSystemEventHandler):
    """triggers re-indexing"""

    __logger: Logger
    __lock: Lock
    __ingester: Ingester
    __path: str
    __reindex: Callable[[], None]

    def __init__(
        self,
        ingester: Ingester,
        path: str,
        logger: Logger,
        debounce_seconds: float = 1.0,
    ):
        self.__ingester = ingester
        self.__logger = logger
        self.__lock = Lock()
        self.__path = path
        self.__reindex = debounce(debounce_seconds)(self.reindex_now)

    def on_any_event(self, event: FileSystemEvent) -> None:
        """called when any event occurs"""
        self.__reindex()

    def reindex_now(self, initialize: bool = False, force: bool = False) -> None:
        """triggers a re-indexing procedure, and logs in case of failure"""

        with self.__lock:
            conn = self.__ingester.conn
            conn.execute("BEGIN;")

            ok = True
            try:
                self.__reindex_impl(initialize=initialize)
            except Exception as e:
                self.__logger.error(f"failed to ingest: {e}")
                ok = False

            if ok or force:
                self.__logger.info("committing indexed ontologies")
                conn.commit()
            else:
                self.__logger.error("rolling back indexed ontologies")
                conn.rollback()

    def __reindex_impl(self, initialize: bool = False) -> None:
        """re-indexing implementation"""

        failures: list[str] = []
        try:
            _, failures = self.__ingester(
                self.__path, initialize=initialize, truncate=True
            )
        except AssertionError as err:
            self.__logger.error("unable to ingest %r: %s", self.__path, err)

        if len(failures) > 0:
            raise AssertionError(
                f"failed to ingest {",".join([repr(f) for f in failures])}"
            )
