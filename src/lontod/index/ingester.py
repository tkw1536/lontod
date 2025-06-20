"""ingestion functionality."""

from logging import Logger
from pathlib import Path
from sqlite3 import Connection
from typing import final

from rdflib import Graph

from lontod.ontologies import owl_ontology
from lontod.ontologies.ontology import slug_from_path
from lontod.utils.ns import BrokenSplitNamespaceManager

from .indexer import Indexer


@final
class Ingester:
    """high-level functionality for ingesting ontologies."""

    __indexer: Indexer
    __logger: Logger

    def __init__(
        self,
        indexer: Indexer,
        html_languages: list[str],
        logger: Logger,
    ) -> None:
        """Create a new ingester."""
        self.__indexer = indexer
        self.__logger = logger
        self.html_languages = html_languages

    @property
    def conn(self) -> Connection:
        """Connection used by this ingester."""
        return self.__indexer.conn

    def __call__(
        self,
        *paths: Path,
        initialize: bool = True,
        truncate: bool = False,
        remove: bool = False,
    ) -> tuple[list[str], list[str]]:
        """Entrypoint for ingesting data.

        Ingests (or removes) data from the given paths into the database.
        Uses the indexers database connection, and does not perform any transaction logic.
        This should be handled by the caller.

        Args:
            paths (str): List of paths (or slugs in case of removal) to remove from the database.
            initialize (bool, optional): Initialize the database. Defaults to True.
            truncate (bool, optional): Delete all existing entries from the database. Defaults to False.
            remove (bool, optional): Instead of indexing the given paths, remove them. Defaults to False.

        Returns:
            tuple[list[str], list[str]]: A list of successful and failed indexed slugs and files.

        """
        if initialize:
            self.__logger.info("initializing schema")
            self.__indexer.initialize_schema()

        if truncate:
            self.__logger.info("truncating database")
            self.__indexer.truncate()

        if remove:
            for path in paths:
                self.__indexer.remove(slug_from_path(path))
            return [], []

        successful: list[str] = []
        failed: list[str] = []
        for path in paths:
            try:
                success, fail = self.ingest(path)
                successful += success
                failed += fail
            except AssertionError as err:
                self.__logger.exception("unable to ingest %r", path, exc_info=err)
                failed += [path.as_posix()]

        return successful, failed

    def ingest(self, path: Path) -> tuple[list[str], list[str]]:
        """Ingests a file or a directory and return a tuple of successful indexes and failed indexes."""
        if path.is_file():
            slug = self._ingest_file(path)
            if not isinstance(slug, str):
                return [], [path.as_posix()]
            return [slug], []

        if path.is_dir():
            return self._ingest_directory(path)

        msg = f"{path!r} is neither a file nor a directory"
        raise AssertionError(msg)

    def _ingest_directory(self, directory: Path) -> tuple[list[str], list[str]]:
        """Ingests all ontologies from the given directory."""
        ingested = []
        failed = []

        for file in directory.iterdir():
            # skip file that starts with "."
            if file.name.startswith("."):
                continue
            slug = self._ingest_file(file)
            if slug is None:
                failed.append(file.as_posix())
                continue

            ingested.append(slug)

        return ingested, failed

    def _ingest_file(self, path: Path) -> str | None:
        """Ingests an ontology from a single file."""
        if not path.is_file():
            self.__logger.info("skipping import of %r: Not a file", path)
            return None

        self.__logger.debug("parsing graph data at %r", path)
        g = Graph()
        g.namespace_manager = BrokenSplitNamespaceManager(g)
        try:
            g.parse(path)
        except Exception as err:
            self.__logger.exception(
                "unable to parse graph data at %r: %s", path, exc_info=err
            )
            return None

        self.__logger.debug("reading OWL ontology at %r", path)
        owl = None
        try:
            owl = owl_ontology(self.__logger, g, self.html_languages)
        except Exception as err:
            self.__logger.exception(
                "unable to read OWL ontology at %r",
                path.as_posix(),
                exc_info=err,
            )
            return None

        self.__logger.debug("inserting ontology %r from %r", owl.uri, str(path))
        slug = slug_from_path(path)
        try:
            self.__indexer.upsert(slug, owl)
        except Exception as err:
            self.__logger.exception(
                "unable to index ontology %r from %r",
                owl.uri,
                path.as_posix(),
                exc_info=err,
            )
            raise

        self.__logger.info(
            "indexed ontology %r from %s as %r", owl.uri, str(path), slug
        )
        return slug
