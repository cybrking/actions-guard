"""Logging setup for ActionsGuard."""

import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


def setup_logger(
    name: str = "actionsguard",
    level: int = logging.INFO,
    verbose: bool = False
) -> logging.Logger:
    """
    Set up logger with Rich formatting.

    Args:
        name: Logger name
        level: Logging level
        verbose: Enable verbose logging

    Returns:
        Configured logger instance
    """
    if verbose:
        level = logging.DEBUG

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers = []

    # Add Rich handler
    handler = RichHandler(
        console=Console(stderr=True),
        rich_tracebacks=True,
        tracebacks_show_locals=verbose,
    )
    handler.setLevel(level)

    formatter = logging.Formatter(
        "%(message)s",
        datefmt="[%X]",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False

    return logger
