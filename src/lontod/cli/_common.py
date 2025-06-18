"""Shared cli functionality"""

from argparse import ArgumentParser
from logging import CRITICAL, DEBUG, INFO, WARNING, Logger, getLogger
from os import environ
from pathlib import Path
from typing import Iterable, TypeVar

from piplicenses_lib import FromArg, get_packages

# spellchecker:words fsevents


def legal_info(logger: Logger) -> None:
    """Logs legal information"""
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

    with (Path(__file__).parent.parent / "html" / "NOTICE").open("r") as file:
        logger.debug(file.read())


T = TypeVar("T")


def _first(items: Iterable[T]) -> T | None:
    """returns the first value contained in an iterator or None"""
    for item in items:
        return item
    return None


def file_or_none(env: str) -> str | None:
    """reads a file from the given environment variable or None"""

    if env not in environ:
        return None
    with open(environ.get(env, ""), "r", encoding="utf-8") as f:
        return f.read()


def list_or_environment(values: list[str] | None, env: str) -> list[str]:
    """returns the values set, or the default one from the environment if unset."""

    if values:
        return values
    arg = environ.get(env, "")
    if arg == "":
        return []
    return arg.split(";")


def add_logging_arg(parser: ArgumentParser) -> None:
    """adds a logging argument to the given parser"""
    parser.add_argument(
        "-l",
        "--log",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set logging level",
    )


def setup_logging(name: str, level: str) -> Logger:
    """perform global logging config and setup a new logger with the given name and level for the"""
    getLogger("asyncio").setLevel(WARNING)
    getLogger("watchdog").setLevel(INFO)
    getLogger("fsevents").setLevel(INFO)
    getLogger("root").setLevel(CRITICAL)

    logger = getLogger(name)
    logger.setLevel(level)
    return logger
