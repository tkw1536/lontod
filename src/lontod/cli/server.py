"""Entrypoint for lontod_server"""

import argparse
import logging
from typing import Optional, Sequence, Text

from uvicorn import run as uv_run

from ..daemon import Handler
from ..db import SqliteConnector, SqliteMode
from ..indexer import QueryPool


def main(args: Optional[Sequence[Text]] = None) -> None:
    """Entrypoint for the lontod_server command"""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-d",
        "--database",
        default="./onto.db",
        help="Database file to index into",
    )
    parser.add_argument(
        "-H",
        "--host",
        default="localhost",
        help="Host to listen on",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8080,
        help="Host to listen on",
    )
    parser.add_argument(
        "-u",
        "--public-url",
        default=None,
        help="Public URL to assume for IRI redirects",
    )
    parser.add_argument(
        "-l",
        "--log",
        default="info",
        help="Set logging level (and enable debug mode)",
    )

    result = parser.parse_args(args)
    run(result.database, result.port, result.host, result.public_url, result.log)


def run(
    db: str, port: int, host: str, public_url: Optional[str], log_level: str
) -> None:
    """Starts the lontod server"""

    # setup logging
    logging.basicConfig(level="logging.{log_level}")
    logger = logging.getLogger("lontod")

    # setup the handler
    app = Handler(
        pool=QueryPool(10, logger, SqliteConnector(db, mode=SqliteMode.READ_ONLY)),
        public_url=public_url,
        logger=logger,
        debug=log_level == "debug",
    )

    try:
        logger.info("Starting server at %s:%s", host, port)
        uv_run(app, log_level="critical", host=host, port=port)
    finally:
        app.pool.teardown()
