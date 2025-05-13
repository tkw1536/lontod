"""ingestion functionality"""

from logging import Logger
from os import listdir
from os.path import isdir, isfile, join
from typing import List, Optional

from rdflib import Graph

from ..ontologies import owl_ontology
from ..ontologies.ontology import slug_from_path
from ..utils.ns import BrokenSplitNamespaceManager
from .indexer import Indexer


class Ingester:
    """high-level functionality for ingesting ontologies"""

    _indexer: Indexer
    _logger: Logger

    def __init__(self, indexer: Indexer, html_languages: List[str], logger: Logger):
        self._indexer = indexer
        self._logger = logger
        self.html_languages = html_languages

    def ingest(self, path: str) -> tuple[list[str], list[str]]:
        """Ingests a file or a directory and return a tuple of successful indexes and failed indexes"""

        if isfile(path):
            slug = self._ingest_file(path)
            if isinstance(slug, str):
                return [slug], []
            else:
                return [], [path]
        elif isdir(path):
            return self._ingest_directory(path)
        else:
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
            self._logger.info("skipping import of %r: Not a file", path)
            return None

        self._logger.info("parsing graph data at %r", path)
        g = Graph()
        g.namespace_manager = BrokenSplitNamespaceManager(g)
        try:
            g.parse(path)
        except Exception as err:
            self._logger.error("unable to parse graph data at %r: %s", path, err)
            return None

        self._logger.debug("reading OWL ontology at %r", path)
        owl = None
        try:
            owl = owl_ontology(g, self.html_languages)
        except Exception as err:
            self._logger.error("unable to read OWL ontology at %r: %s", path, err)
            return None

        self._logger.debug("inserting ontology %s from %r", owl.uri, path)
        slug = slug_from_path(path)
        try:
            self._indexer.upsert(slug, owl)
        except Exception as err:
            self._logger.error(
                "unable to index ontology %s from %r: %s", owl.uri, path, err
            )
            raise

        self._logger.info("indexed ontology %s from %r as %r", owl.uri, path, slug)
        return slug
