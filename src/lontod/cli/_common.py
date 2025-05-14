"""Shared cli functionality"""

from argparse import ArgumentParser
from logging import INFO, WARNING, CRITICAL, Logger, getLogger
from os import environ

#spellchecker:words fsevents

def lang_or_environment(langs: list[str] | None) -> list[str]:
    """returns the set languages argument, or the default one form the environment if unset."""
    if langs:
        return langs
    arg = environ.get("LONTOD_LANGUAGES", "")
    if arg == "":
        return []
    return arg.split(",")


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
