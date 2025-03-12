import logging
from os import listdir
from os.path import isfile, join
from typing import Optional

from rdflib import Graph

from ..ontologies import owl_ontology
from ..ontologies.ontology import slug_from_path
from .indexer import Indexer


class Ingester:
    def __init__(self, indexer: Indexer, logger: logging.Logger):
        self.indexer = indexer
        self.logger = logger

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
        if not isfile(path):
            self.logger.info("Skipping import of %r: Not a file", path)
            return None

        self.logger.info("Parsing graph data at %r", path)
        g = Graph()
        try:
            g.parse(path)
        except Exception as err:
            self.logger.error("Unable to parse graph data at %r: %s", path, err)
            return None

        self.logger.debug("Reading OWL ontology at %r", path)
        owl = None
        try:
            owl = owl_ontology(g)
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
