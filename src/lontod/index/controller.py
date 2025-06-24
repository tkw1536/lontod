"""implements high level functionality for ingestion."""

from collections.abc import Callable, Sequence
from logging import Logger
from pathlib import Path
from sqlite3 import Connection
from threading import Lock
from typing import final, override

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from lontod.utils.debounce import debounce

from .indexer import Indexer
from .ingester import Ingester


@final
class Controller:
    """controls indexing and optionally watches the given directories."""

    __conn: Connection
    __observer: BaseObserver | None = None
    __paths: Sequence[Path]
    __logger: Logger
    __lock: Lock
    __html_languages: Sequence[str | None]
    __ingester: Ingester

    def __init__(
        self,
        conn: Connection,
        paths: Sequence[Path],
        html_languages: Sequence[str | None],
        logger: Logger,
    ) -> None:
        """Create a new controller."""
        self.__conn = conn
        self.__logger = logger
        self.__paths = paths
        self.__html_languages = html_languages
        self.__lock = Lock()
        self.__ingester = Ingester(
            Indexer(self.__conn, self.__logger),
            self.__html_languages,
            self.__logger,
        )

    def index_and_commit(self) -> None:
        """Perform an indexing operation, and always commits the result."""
        with self.__lock:
            self.__logger.info("ingesting paths %r", self.__paths)
            self.__conn.execute("BEGIN;")
            self.__ingester(*self.__paths, initialize=True, truncate=False)
            self.__conn.commit()

    def start_watching(self) -> None:
        """Start watching and automatically reindexing."""
        if self.__observer is not None:
            msg = "already started"
            raise AssertionError(msg)

        handler = ReIndexingHandler(
            self.__ingester,
            self.__lock,
            self.__paths,
            self.__logger,
        )

        self.__observer = Observer()
        for path in self.__paths:
            self.__logger.info("starting to watch %r", path)
            self.__observer.schedule(handler, str(path), recursive=True)
        self.__observer.start()

    def close(self) -> None:
        """Close the connection (and any possible observers)."""
        self.__conn.close()

        if self.__observer is not None:
            self.__logger.info("stopping watch of %r", self.__paths)
            self.__observer.stop()


@final
class ReIndexingHandler(FileSystemEventHandler):
    """triggers re-indexing."""

    __logger: Logger
    __lock: Lock
    __ingester: Ingester
    __paths: Sequence[Path]
    __reindex: Callable[[], None]

    def __init__(
        self,
        ingester: Ingester,
        lock: Lock,
        paths: Sequence[Path],
        logger: Logger,
        debounce_seconds: float = 1.0,
    ) -> None:
        """Create a new ReIndexingHandler."""
        self.__ingester = ingester
        self.__logger = logger
        self.__lock = lock
        self.__paths = paths
        self.__reindex = debounce(debounce_seconds)(self.reindex_now)

    @override
    def on_any_event(self, event: FileSystemEvent) -> None:
        self.__reindex()

    def reindex_now(self, initialize: bool = False, force: bool = False) -> None:
        """Triggers a re-indexing procedure, and logs in case of failure."""
        with self.__lock:
            conn = self.__ingester.conn
            conn.execute("BEGIN;")

            ok = True
            try:
                self.__reindex_impl(initialize=initialize)
            except Exception as e:
                self.__logger.exception("failed to ingest", exc_info=e)
                ok = False

            if ok or force:
                self.__logger.info("committing indexed ontologies")
                conn.commit()
            else:
                self.__logger.error("rolling back indexed ontologies")
                conn.rollback()

    def __reindex_impl(self, initialize: bool = False) -> None:
        """re-indexing implementation."""
        failures: list[str] = []
        try:
            _, failures = self.__ingester(
                *self.__paths,
                initialize=initialize,
                truncate=True,
            )
        except AssertionError as err:
            self.__logger.exception("unable to ingest %r", self.__paths, exc_info=err)

        if len(failures) > 0:
            msg = f"failed to ingest {','.join([repr(f) for f in failures])}"
            raise AssertionError(
                msg,
            )
