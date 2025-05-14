"""Entrypoint for lontod_index"""

import argparse
from os import environ
from typing import List, Optional, Sequence, Text

from ..index import Indexer, Ingester
from ..sqlite import Connector
from ._common import add_logging_arg, list_or_environment, setup_logging


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
        default=environ.get("LONTOD_DB", "./onto.db"),
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
        list_or_environment(result.input, "LONTOD_PATHS"),
        result.clean,
        list_or_environment(result.language, "LONTOD_LANG"),
        result.simulate,
        result.database,
        result.remove,
        result.log,
    )


def run(
    paths: list[str],
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

        ingest_ok = False
        try:
            ingester(*paths, initialize=True, truncate=clean, remove=remove)
            ingest_ok = True
        except Exception as err:
            logger.error("ingestion failed %s", err)

        if simulate:
            logger.info("simulate was provided, rolling back transaction")
            conn.rollback()
            return

        if ingest_ok:
            logger.info("committing changes")
            conn.commit()
        else:
            logger.info("rolling back changes")
            conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
