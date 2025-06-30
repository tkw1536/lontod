"""Entrypoint for lontod_index."""

import argparse
from collections.abc import Sequence
from os import environ
from pathlib import Path

from lontod.index import Indexer, Ingester
from lontod.sqlite import Connector

from ._common import (
    add_logging_arg,
    legal_info,
    list_or_environment,
    setup_logging,
)


def main(args: Sequence[str] | None = None) -> None:
    """Entrypoint for the lontod_index executable."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input",
        nargs="+",
        help="Path(s) to input file(s) or directories(s) to read",
    )
    parser.add_argument(
        "-d",
        "--database",
        default=environ.get("LONTOD_DB", "./lontod.index"),
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

    result = parser.parse_args(args)
    run(
        [Path(p) for p in list_or_environment(result.input, "LONTOD_PATHS")],
        result.clean,
        result.simulate,
        result.database,
        result.remove,
        result.log,
    )


def run(  # noqa: PLR0913
    paths: Sequence[Path],
    clean: bool,
    simulate: bool,
    db: str,
    remove: bool,
    log_level: str,
) -> None:
    """Begins an indexing process."""
    # setup logging
    logger = setup_logging("lontod_index", log_level)
    legal_info(logger)

    connector = Connector(db)
    logger.info("opening database at %r", connector.connect_url)
    conn = connector.connect()

    indexer = Indexer(conn, logger)
    ingester = Ingester(indexer, logger)

    try:
        # create a transaction
        conn.execute("BEGIN;")

        ingest_ok = False
        try:
            ingester(*paths, initialize=True, truncate=clean, remove=remove)
            ingest_ok = True
        except Exception as err:
            logger.exception("ingestion failed", exc_info=err)

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
