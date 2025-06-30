"""Shared cli functionality."""

from argparse import ArgumentParser
from collections.abc import Iterable
from logging import CRITICAL, DEBUG, INFO, WARNING, Logger, basicConfig, getLogger
from os import environ
from pathlib import Path

from piplicenses_lib import FromArg, get_packages

# spellchecker:words fsevents piplicenses


def legal_info(logger: Logger) -> None:
    """Log legal information."""
    logger.info("Lontod (c) Dr. Tom Wiesing <tom@tkw01536.de>, all rights reserved. ")
    if logger.level > DEBUG:
        logger.info("Set log level to DEBUG to view licensing information. ")
        return

    for package in get_packages(FromArg.META):
        logger.debug(
            "package %s by %s licensed under %s",
            package.name,
            package.author,
            package.license,
        )
        text = _first(package.license_texts)
        logger.debug(text)

    with (Path(__file__).parent.parent / "ontologies" / "NOTICE").open("r") as file:
        logger.debug(file.read())


def _first[T](items: Iterable[T]) -> T | None:
    """Return the first value contained in an iterator or None."""
    for item in items:
        return item
    return None


def file_or_none(env: str) -> str | None:
    """Read a file from the given environment variable or None."""
    if env not in environ:
        return None
    return Path(environ.get(env, "")).read_text(encoding="utf-8")


def list_or_environment(
    values: list[str] | None, env: str, default: str = ""
) -> list[str]:
    """Return the values set, or the default one from the environment if unset."""
    if values:
        return values
    arg = environ.get(env, default)
    if arg == "":
        return []
    return arg.split(";")


def add_logging_arg(parser: ArgumentParser) -> None:
    """Add a logging argument to the given parser."""
    parser.add_argument(
        "-l",
        "--log",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set logging level",
    )


def setup_logging(name: str, level: str) -> Logger:
    """Perform global logging config and setup a new logger with the given name and level for the."""
    basicConfig()

    # turn down the verbosity of a bunch of these
    getLogger("asyncio").setLevel(WARNING)
    getLogger("watchdog").setLevel(INFO)
    getLogger("fsevents").setLevel(INFO)
    getLogger("root").setLevel(CRITICAL)

    # and get our logger!
    logger = getLogger(name)
    logger.setLevel(level)

    return logger
