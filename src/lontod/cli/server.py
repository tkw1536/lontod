"""Entrypoint for lontod_server"""

import argparse
from os import environ
from typing import Optional, Sequence, Text

from uvicorn import run as uv_run

from ..daemon import Handler
from ..index import QueryPool
from ..sqlite import Connector, Mode
from ._common import add_logging_arg, setup_logging


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
        default=environ.get("LONTOD_HOST") or "localhost",
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

    add_logging_arg(parser)

    result = parser.parse_args(args)
    run(result.database, result.port, result.host, result.public_url, result.log)


def run(
    db: str, port: int, host: str, public_url: Optional[str], log_level: str
) -> None:
    """Starts the lontod server"""

    # setup logging
    logger = setup_logging("lontod_server", log_level)

    # setup the handler
    app = Handler(
        pool=QueryPool(10, logger, Connector(db, mode=Mode.READ_ONLY)),
        public_url=public_url,
        logger=logger,
        debug=log_level == "debug",
    )

    try:
        logger.info("Starting server at %s:%s", host, port)
        uv_run(app, log_level="error", host=host, port=port)
    finally:
        app.pool.teardown()


if __name__ == "__main__":
    main()
