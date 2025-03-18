"""ingestion functionality"""

import logging
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

    def __init__(
        self, indexer: Indexer, html_languages: List[str], logger: logging.Logger
    ):
        self.indexer = indexer
        self.logger = logger
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
            self.logger.info("Skipping import of %r: Not a file", path)
            return None

        self.logger.info("Parsing graph data at %r", path)
        g = Graph()
        g.namespace_manager = BrokenSplitNamespaceManager(g)
        try:
            g.parse(path)
        except Exception as err:
            self.logger.error("Unable to parse graph data at %r: %s", path, err)
            return None

        self.logger.debug("Reading OWL ontology at %r", path)
        owl = None
        try:
            owl = owl_ontology(g, self.html_languages)
        except Exception as err:
            self.logger.error("Unable to read OWL ontology at %r: %s", path, err)
            return None

        self.logger.debug("Inserting ontology %s from %r", owl.uri, path)
        slug = slug_from_path(path)
        try:
            self.indexer.upsert(slug, owl)
        except Exception as err:
            self.logger.error(
                "Unable to index ontology %s from %r: %s", owl.uri, path, err
            )
            raise

        self.logger.info("Indexed ontology %s from %r as %r", owl.uri, path, slug)
        return slug
