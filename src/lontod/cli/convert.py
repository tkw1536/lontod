"""Entrypoint for lontod_server."""

import argparse
from collections.abc import Sequence
from pathlib import Path
from sys import stdout

from lontod.index import Controller, Query
from lontod.ontologies.types import media_types
from lontod.sqlite import Connector, Mode

from ._common import (
    add_logging_arg,
    legal_info,
    setup_logging,
)

MEDIA_DICT = dict((*media_types(), ("html", "text/html")))


def main(args: Sequence[str] | None = None) -> None:
    """Entrypoint for the lontod_convert command."""
    parser = argparse.ArgumentParser(
        description="Convert an ontology into a specific format."
    )

    parser.add_argument(
        "input",
        help="Path to input file",
    )
    parser.add_argument(
        "--format",
        "-f",
        default="xml",
        choices=tuple(MEDIA_DICT.keys()) + tuple(MEDIA_DICT.values()),
        help="Media Type or formats of output file to generate.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="File to write output to. Defaults to STDOUT.",
    )
    add_logging_arg(parser)

    result = parser.parse_args(args)

    run(
        Path(result.input),
        MEDIA_DICT.get(result.format, result.format),
        Path(result.output) if result.output is not None else None,
        result.log,
    )


def run(
    path: Path,
    media_type: str,
    output: Path | None,
    log_level: str,
) -> None:
    """Start the lontod server."""
    # setup logging
    logger = setup_logging("lontod_convert", log_level)
    legal_info(logger)

    # create a new connection and controller
    connector = Connector("", mode=Mode.READ_WRITE_CREATE)
    logger.info("opening database at %r", connector.connect_url)
    conn = connector.connect()

    try:
        # create a controller and index the file
        controller = Controller(conn, [path], logger)
        controller.index_and_commit()

        # build a query
        query = Query(conn, logger)

        # find the ontology
        ontologies = list(query.list_ontologies())
        if len(ontologies) != 1:
            msg = "ontology was not indexed"
            raise AssertionError(msg)
        ontology = ontologies[0]

        # find the encoding of the file
        data = query.get_data(ontology.identifier, media_type)
        if data is None:
            msg = f"ontology does not contain media_type {media_type}"
            raise AssertionError(msg)

        # and dump the result
        if output is None:
            stdout.buffer.write(data)
        else:
            output.write_bytes(data)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
