"""implements high level functionality for ingestion"""

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
class Controller:
    """controls indexing and optionally watches the given directories"""

    __conn: Connection
    __observer: BaseObserver | None = None
    __paths: list[str]
    __logger: Logger
    __lock: Lock
    __html_languages: list[str]
    __ingester: Ingester

    def __init__(
        self,
        conn: Connection,
        paths: list[str],
        html_languages: list[str],
        logger: Logger,
    ):
        self.__conn = conn
        self.__logger = logger
        self.__paths = paths
        self.__html_languages = html_languages
        self.__lock = Lock()
        self.__ingester = Ingester(
            Indexer(self.__conn, self.__logger), self.__html_languages, self.__logger
        )

    def index_and_commit(self) -> None:
        """Performs an indexing operation, and always commits the result"""

        with self.__lock:
            self.__logger.info(f"ingesting paths {self.__paths!r}")
            self.__conn.execute("BEGIN;")
            self.__ingester(*self.__paths, initialize=True, truncate=False)
            self.__conn.commit()

    def start_watching(self) -> None:
        """starts watching and automatically reindexing"""

        if self.__observer is not None:
            raise AssertionError("already started")

        handler = ReIndexingHandler(
            self.__ingester, self.__lock, self.__paths, self.__logger
        )

        self.__observer = Observer()
        for path in self.__paths:
            self.__logger.info(f"starting to watch {path!r}")
            self.__observer.schedule(handler, path, recursive=True)
        self.__observer.start()

    def close(self) -> None:
        """closes the connection (and any possible observers)"""
        self.__conn.close()

        if self.__observer is not None:
            self.__logger.info(f"stopping watch of {self.__paths!r}")
            self.__observer.stop()


@final
class ReIndexingHandler(FileSystemEventHandler):
    """triggers re-indexing"""

    __logger: Logger
    __lock: Lock
    __ingester: Ingester
    __paths: list[str]
    __reindex: Callable[[], None]

    def __init__(
        self,
        ingester: Ingester,
        lock: Lock,
        paths: list[str],
        logger: Logger,
        debounce_seconds: float = 1.0,
    ):
        self.__ingester = ingester
        self.__logger = logger
        self.__lock = lock
        self.__paths = paths
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
                *self.__paths, initialize=initialize, truncate=True
            )
        except AssertionError as err:
            self.__logger.error("unable to ingest %r: %s", self.__paths, err)

        if len(failures) > 0:
            raise AssertionError(
                f"failed to ingest {",".join([repr(f) for f in failures])}"
            )
