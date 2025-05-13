"""Entrypoint for lontod_index"""

import argparse
from typing import List, Optional, Sequence, Text

from ..index import Indexer, Ingester
from ..sqlite import Connector
from ._common import add_logging_arg, setup_logging


def main(args: Optional[Sequence[Text]] = None) -> None:
    """Main Entry point for the lontod_index executable"""
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
    add_logging_arg(parser)
    parser.add_argument(
        "-s",
        "--simulate",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Simulate import by using a dummy transaction",
    )
    parser.add_argument(
        "-R",
        "--remove",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Instead of adding new entries, remove ontologies with slugs or URIs given in input. If no slugs are provided, remove all ontologies. ",
    )
    parser.add_argument(
        "-L",
        "--languages",
        nargs="*",
        help="Specify language preferences for the given ontology",
    )

    result = parser.parse_args(args)
    run(
        result.input,
        result.clean,
        result.languages or [],
        result.simulate,
        result.database,
        result.remove,
        result.log,
    )


def run(
    paths: str,
    clean: bool,
    html_languages: List[str],
    simulate: bool,
    db: str,
    remove: bool,
    log_level: str,
) -> None:
    """Begins an indexing process"""

    # setup logging
    logger = setup_logging("lontod_index", log_level)

    connector = Connector(db)
    logger.info("opening database at %r", connector.connect_url)
    conn = connector.connect()

    indexer = Indexer(conn, logger)
    ingester = Ingester(indexer, html_languages, logger)

    try:
        # create a transaction
        conn.execute("BEGIN;")

        logger.info("initializing schema")
        indexer.initialize_schema()

        if not remove:
            if clean:
                logger.info("cleaning up database")
                indexer.truncate()

            for path in paths:
                try:
                    ingester.ingest(path)
                except AssertionError as err:
                    logger.error("unable to ingest %r: %s", path, err)
        else:
            for slug in paths:
                logger.info("removing %r", slug)
                indexer.remove(slug, slug)

        if simulate:
            logger.info("simulate was provided, rolling back transaction")
            conn.rollback()
            return

        logger.info("committing changes")
        conn.commit()

        return
    finally:
        conn.close()


if __name__ == "__main__":
    main()
