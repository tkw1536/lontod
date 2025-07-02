"""Entrypoint for lontod_server."""

import argparse
from collections.abc import Sequence
from os import environ
from pathlib import Path
from threading import Thread

from uvicorn import run as uv_run

from lontod.daemon import Handler
from lontod.index import Controller, QueryPool
from lontod.sqlite import Connector, Mode

from ._common import (
    add_logging_arg,
    file_or_none,
    legal_info,
    list_or_environment,
    setup_logging,
)


def main(args: Sequence[str] | None = None) -> None:
    """Entrypoint for the lontod_server command."""
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
        "-H",
        "--host",
        default=environ.get("LONTOD_HOST") or "localhost",
        help="Host to listen on",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=environ.get("LONTOD_PORT", "8080"),
        help="Host to listen on",
    )
    parser.add_argument(
        "-D",
        "--public-domain",
        default=None,
        help="Public Domain to assume for IRI redirects",
    )
    parser.add_argument(
        "-r",
        "--ontology-route",
        default=environ.get("LONTOD_ROUTE", "/"),
        help="Route to serve ontologies from. Must start with a slash",
    )
    parser.add_argument(
        "--insecure-skip-routes",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Skip adding routes blocking dangerous paths",
    )

    add_logging_arg(parser)

    result = parser.parse_args(args)
    run(
        result.database,
        [Path(p) for p in list_or_environment(result.input, "LONTOD_PATHS")],
        result.port,
        result.host,
        result.public_domain,
        result.ontology_route,
        result.insecure_skip_routes,
        result.log,
        result.watch,
    )


def run(  # noqa: PLR0913
    db: str | None,
    paths: Sequence[Path],
    port: int,
    host: str,
    public_domain: str | None,
    ontology_route: str,
    insecure_skip_routes: bool,
    log_level: str,
    watch: bool,
) -> None:
    """Start the lontod server."""
    # setup logging
    logger = setup_logging("lontod_server", log_level)
    legal_info(logger)

    # set the default database
    if db is None and len(paths) == 0:
        db = environ.get("LONTOD_DB", "./lontod.index")

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

    # an optional controller for indexing
    indexing_thread: Thread | None = None
    indexing_controller: Controller | None = None
    if len(paths) > 0:

        def _index() -> None:
            nonlocal indexing_controller
            logger.info("opening database at %r", index_conn.connect_url)
            conn = index_conn.connect()

            # create a watcher and use the ingester to ingest!
            indexing_controller = Controller(conn, paths, logger)
            indexing_controller.index_and_commit()

            # start the watcher if given
            if watch:
                indexing_controller.start_watching()

        indexing_thread = Thread(target=_index)
        indexing_thread.start()

    if insecure_skip_routes:
        logger.warning("skipping routes blocked for safety, use with caution")

    # setup the handler
    pool = QueryPool(10, logger, server_conn)
    app = Handler(
        pool=pool,
        ontology_route=ontology_route,
        public_domain=public_domain,
        insecure_skip_routes=insecure_skip_routes,
        logger=logger,
        debug=log_level == "debug",
        index_html_header=file_or_none("LONTOD_INDEX_HTML_HEADER"),
        index_html_footer=file_or_none("LONTOD_INDEX_HTML_FOOTER"),
        index_txt_header=file_or_none("LONTOD_INDEX_TXT_HEADER"),
        index_txt_footer=file_or_none("LONTOD_INDEX_TXT_FOOTER"),
    )

    try:
        logger.info("starting server at %s:%s", host, port)
        uv_run(app, log_level="error", host=host, port=port)
    finally:
        pool.teardown()
        if indexing_thread is not None:
            indexing_thread.join()
            if indexing_controller is not None:
                indexing_controller.close()


if __name__ == "__main__":
    main()
