"""Entrypoint for lontod_server"""

import argparse
from os import environ
from typing import Optional, Sequence, Text

from uvicorn import run as uv_run

from ..daemon import Handler
from ..index import Controller, QueryPool
from ..sqlite import Connector, Mode
from ._common import add_logging_arg, list_or_environment, setup_logging


def main(args: Optional[Sequence[Text]] = None) -> None:
    """Entrypoint for the lontod_server command"""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "input",
        nargs="*",
        help="Path(s) to input file(s) or directories(s) to index or watch",
    )
    parser.add_argument(
        "-d",
        "--database",
        default=None,
        help="Database file to index into (default: './onto.db' or in-memory when watching)",
    )
    parser.add_argument(
        "-w",
        "--watch",
        action=argparse.BooleanOptionalAction,
        help="Instead of only indexing once, re-index the files and folder every time they change",
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
        list_or_environment(result.input, "LONTOD_PATHS"),
        result.port,
        result.host,
        result.public_url,
        result.log,
        result.watch,
        list_or_environment(result.language, "LONTOD_LANG"),
    )


def run(
    db: Optional[str],
    paths: list[str],
    port: int,
    host: str,
    public_url: Optional[str],
    log_level: str,
    watch: bool,
    languages: list[str],
) -> None:
    """Starts the lontod server"""
    # setup logging
    logger = setup_logging("lontod_server", log_level)

    # set the default database
    if db is None and len(paths) == 0:
        db = environ.get("LONTOD_DB", "./onto.db")

    if watch and len(paths) == 0:
        logger.fatal("--watch given, but no paths to watch provided")
        return

    server_conn: Connector
    index_conn: Connector
    if isinstance(db, str):
        server_conn = Connector(db, mode=Mode.READ_ONLY)
        index_conn = Connector(db, mode=Mode.READ_WRITE_CREATE)
    else:
        server_conn = Connector("lontod", mode=Mode.MEMORY_SHARED_CACHE)
        index_conn = server_conn

    # an optional controller
    controller: Controller | None = None
    if len(paths) > 0:
        logger.info("opening database at %r", index_conn.connect_url)
        conn = index_conn.connect()

        # create a watcher and use the ingester to ingest!
        controller = Controller(conn, paths, languages, logger)
        controller.index_and_commit()

        # start the watcher if given
        if watch:
            controller.start_watching()

    # setup the handler
    app = Handler(
        pool=QueryPool(10, logger, server_conn),
        public_url=public_url,
        logger=logger,
        debug=log_level == "debug",
    )

    try:
        logger.info("starting server at %s:%s", host, port)
        uv_run(app, log_level="error", host=host, port=port)
    finally:
        if controller is not None:
            controller.close()
        app.pool.teardown()


if __name__ == "__main__":
    main()
