"""Entrypoint for lontod_server"""

import argparse
from os import environ
from typing import Optional, Sequence, Text

from uvicorn import run as uv_run

from ..daemon import Handler
from ..index import QueryPool, Watcher
from ..sqlite import Connector, Mode
from ._common import add_logging_arg, setup_logging


def main(args: Optional[Sequence[Text]] = None) -> None:
    """Entrypoint for the lontod_server command"""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-d",
        "--database",
        default=None,
        help="Database file to index into (default: './onto.db' or in-memory when watching)",
    )
    parser.add_argument(
        "-w",
        "--watch",
        default=None,
        help="Watch specific folder for changes in ontology files",
    )
    parser.add_argument(
        "-L",
        "--language",
        nargs="*",
        help="Specify language preferences for watched ontologies",
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
    run(
        result.database,
        result.port,
        result.host,
        result.public_url,
        result.log,
        result.watch,
        result.language or [],
    )


def run(
    db: Optional[str],
    port: int,
    host: str,
    public_url: Optional[str],
    log_level: str,
    watch: Optional[str],
    languages: list[str],
) -> None:
    """Starts the lontod server"""

    # set the default database
    if watch is None and db is None:
        db = "./onto.db"

    connector_server: Connector
    connector_watcher: Connector
    if isinstance(db, str):
        connector_server = Connector(db, mode=Mode.READ_ONLY)
        connector_watcher = Connector(db, mode=Mode.READ_WRITE_CREATE)
    else:
        connector_server = Connector("lontod", mode=Mode.MEMORY_SHARED_CACHE)
        connector_watcher = connector_server

    # setup logging
    logger = setup_logging("lontod_server", log_level)

    watcher = None
    if watch is not None:
        logger.info("opening database at %r", connector_watcher.connect_url)
        conn = connector_watcher.connect()

        watcher = Watcher(conn, watch, languages, logger)
        watcher.start()

    # setup the handler
    app = Handler(
        pool=QueryPool(10, logger, connector_server),
        public_url=public_url,
        logger=logger,
        debug=log_level == "debug",
    )

    try:
        logger.info("starting server at %s:%s", host, port)
        uv_run(app, log_level="error", host=host, port=port)
    finally:
        if watcher is not None:
            watcher.close()
        app.pool.teardown()


if __name__ == "__main__":
    main()
