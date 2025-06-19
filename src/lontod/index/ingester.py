"""ingestion functionality"""

from logging import Logger
from os import listdir
from os.path import isdir, isfile, join
from sqlite3 import Connection
from typing import List, Optional, final

from rdflib import Graph

from ..ontologies import owl_ontology
from ..ontologies.ontology import slug_from_path
from ..utils.ns import BrokenSplitNamespaceManager
from .indexer import Indexer


@final
class Ingester:
    """high-level functionality for ingesting ontologies"""

    __indexer: Indexer
    __logger: Logger

    def __init__(self, indexer: Indexer, html_languages: List[str], logger: Logger):
        self.__indexer = indexer
        self.__logger = logger
        self.html_languages = html_languages

    @property
    def conn(self) -> Connection:
        """connection used by this ingester"""
        return self.__indexer.conn

    def __call__(
        self,
        *paths: str,
        initialize: bool = True,
        truncate: bool = False,
        remove: bool = False,
    ) -> tuple[list[str], list[str]]:
        """Ingests (or removes) data from the given paths into the database.
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
            for slug in paths:
                self.__indexer.remove(slug)
            return [], []

        successful: list[str] = []
        failed: list[str] = []
        for path in paths:
            try:
                success, fail = self.ingest(path)
                successful += success
                failed += fail
            except AssertionError as err:
                self.__logger.error("unable to ingest %r: %s", path, err)
                failed += [path]

        return successful, failed

    def ingest(self, path: str) -> tuple[list[str], list[str]]:
        """Ingests a file or a directory and return a tuple of successful indexes and failed indexes"""

        if isfile(path):
            slug = self._ingest_file(path)
            if not isinstance(slug, str):
                return [], [path]
            return [slug], []

        if isdir(path):
            return self._ingest_directory(path)

        raise AssertionError(f"{path!r} is neither a file nor a directory")

    def _ingest_directory(self, directory: str) -> tuple[list[str], list[str]]:
        """Ingests all ontologies from the given directory"""
        ingested = []
        failed = []

        for file in listdir(directory):
            # skip file that starts with "."
            if file.startswith("."):
                continue
            path = join(directory, file)
            slug = self._ingest_file(path)
            if slug is None:
                failed.append(path)
                continue

            ingested.append(slug)

        return ingested, failed

    def _ingest_file(self, path: str) -> Optional[str]:
        """Ingests an ontology from a single file"""
        if not isfile(path):
            self.__logger.info("skipping import of %r: Not a file", path)
            return None

        self.__logger.debug("parsing graph data at %r", path)
        g = Graph()
        g.namespace_manager = BrokenSplitNamespaceManager(g)
        try:
            g.parse(path)
        except Exception as err:
            self.__logger.error("unable to parse graph data at %r: %s", path, err)
            return None

        self.__logger.debug("reading OWL ontology at %r", path)
        owl = None
        try:
            owl = owl_ontology(self.__logger, g, self.html_languages)
        except Exception as err:
            self.__logger.error(
                "unable to read OWL ontology at %r: %s", path, err, exc_info=err
            )
            return None

        self.__logger.debug("inserting ontology %r from %r", owl.uri, path)
        slug = slug_from_path(path)
        try:
            self.__indexer.upsert(slug, owl)
        except Exception as err:
            self.__logger.error(
                "unable to index ontology %r from %r: %s", owl.uri, path, err
            )
            raise

        self.__logger.info("indexed ontology %r from %r as %r", owl.uri, path, slug)
        return slug
