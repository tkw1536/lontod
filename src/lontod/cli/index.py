import argparse
import logging
from os.path import isdir, isfile
from typing import Optional, Sequence, Text

from ..db import SqliteConnector
from ..indexer import Indexer, Ingester


def main(args: Optional[Sequence[Text]] = None) -> None:
    """ Main Entry point for the lontod_index executable """
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
    parser.add_argument(
        "-s",
        "--simulate",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Simulate import by using a dummy transaction",
    )

    result = parser.parse_args(args)
    run(result.input, result.clean, result.simulate, result.database, result.log)


def run(paths: str, clean: bool, simulate: bool, db: str, log_level: str) -> None:
    """Begins an indexing process"""

    # setup logging
    logging.basicConfig(level=f"logging.{log_level}")
    logger = logging.getLogger(__name__)

    connector = SqliteConnector(db)
    logger.info("Opening database at %r", connector.connect_url)
    conn = connector.connect()

    indexer = Indexer(conn)
    ingester = Ingester(indexer, logger)

    try:
        # create a transaction
        conn.execute('BEGIN;')

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

        if simulate:
            logger.info('Simulate was provided, rolling back transaction')
            conn.rollback()
            return
        
        logger.info('Committing changes')
        conn.commit()

        return
    finally:
        conn.close()
