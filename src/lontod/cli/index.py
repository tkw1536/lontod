import argparse
import logging
import sqlite3
from os.path import isdir, isfile
from typing import Optional, Sequence, Text

from ..indexer import Indexer, Ingester


def main(args: Optional[Sequence[Text]] = None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input",
        nargs="+",
        help="Path(s) to input file(s) or directories(s) to read",
    )
    parser.add_argument(
        "-d",
        "--database",
        default="./onto.db",
        help="Database file to index into",
    )
    parser.add_argument(
        "-c",
        "--clean",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Remove all old indexed entities",
    )
    parser.add_argument(
        "-l",
        "--log",
        default="info",
        help="Set logging level",
    )

    result = parser.parse_args(args)
    run(result.input, result.clean, result.database, result.log)


def run(paths: str, clean: bool, db: str, log_level: str):
    """Begins an indexing process"""
    # setup logging
    logging.basicConfig(level=f"logging.{log_level}")
    logger = logging.getLogger(__name__)

    logger.info("Opening database at %r", db)
    conn = sqlite3.connect(db)

    indexer = Indexer(conn)
    ingester = Ingester(indexer, logger)

    try:
        logger.info("Initializing schema")
        indexer.initialize_schema()

        if clean:
            logger.info("Cleaning up database")
            indexer.truncate()

        for path in paths:
            if isfile(path):
                ingester.ingest_file(path)
            elif isdir(path):
                ingester.ingest_directory(path)
            else:
                logger.error(
                    "Unable to ingest %r: Neither a path nor a directory", path
                )

        conn.commit()
    finally:
        conn.close()
