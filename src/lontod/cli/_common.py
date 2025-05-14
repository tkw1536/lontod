"""Shared cli functionality"""

from argparse import ArgumentParser
from logging import CRITICAL, INFO, WARNING, Logger, getLogger
from os import environ

# spellchecker:words fsevents


def list_or_environment(values: list[str] | None, env: str) -> list[str]:
    """returns the set languages argument, or the default one form the environment if unset."""
    if values:
        return values
    arg = environ.get(env, "")
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
