"""Shared cli functionality"""

from argparse import ArgumentParser
from logging import WARNING, Logger, getLogger


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

    logger = getLogger(name)
    logger.setLevel(level)
    return logger
