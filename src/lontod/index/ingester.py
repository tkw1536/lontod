"""ingestion functionality"""

from logging import Logger
from os import listdir
from os.path import isfile, join
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

    def ingest_directory(self, directory: str) -> list[str]:
        """Ingests all ontologies from the given directory"""
        ingested = []

        for file in listdir(directory):
            slug = self.ingest_file(join(directory, file))
            if slug is None:
                continue

            ingested.append(slug)

        return ingested

    def ingest_file(self, path: str) -> Optional[str]:
        """Ingests an ontology from a single file"""
        if not isfile(path):
            self._logger.info("Skipping import of %r: Not a file", path)
            return None

        self._logger.info("Parsing graph data at %r", path)
        g = Graph()
        g.namespace_manager = BrokenSplitNamespaceManager(g)
        try:
            g.parse(path)
        except Exception as err:
            self._logger.error("Unable to parse graph data at %r: %s", path, err)
            return None

        self._logger.debug("Reading OWL ontology at %r", path)
        owl = None
        try:
            owl = owl_ontology(g, self.html_languages)
        except Exception as err:
            self._logger.error("Unable to read OWL ontology at %r: %s", path, err)
            return None

        self._logger.debug("Inserting ontology %s from %r", owl.uri, path)
        slug = slug_from_path(path)
        try:
            self._indexer.upsert(slug, owl)
        except Exception as err:
            self._logger.error(
                "Unable to index ontology %s from %r: %s", owl.uri, path, err
            )
            raise

        self._logger.info("Indexed ontology %s from %r as %r", owl.uri, path, slug)
        return slug
