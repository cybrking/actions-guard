"""Logging setup for ActionsGuard."""

import logging
import sys
import json
from datetime import datetime
from typing import Optional, Dict, Any

from rich.console import Console
from rich.logging import RichHandler


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra context fields if present
        if hasattr(record, "repo_name"):
            log_data["repo_name"] = record.repo_name
        if hasattr(record, "scan_id"):
            log_data["scan_id"] = record.scan_id
        if hasattr(record, "duration"):
            log_data["duration_ms"] = record.duration
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code

        # Add any custom fields from extra dict
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "getMessage",
                "repo_name",
                "scan_id",
                "duration",
                "status_code",
            ]:
                log_data[key] = value

        return json.dumps(log_data)


def setup_logger(
    name: str = "actionsguard",
    level: int = logging.INFO,
    verbose: bool = False,
    json_format: bool = False,
) -> logging.Logger:
    """
    Set up logger with Rich or JSON formatting.

    Args:
        name: Logger name
        level: Logging level
        verbose: Enable verbose logging
        json_format: Use JSON structured logging (for production)

    Returns:
        Configured logger instance
    """
    if verbose:
        level = logging.DEBUG

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers = []

    if json_format:
        # JSON structured logging for production
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        handler.setFormatter(JSONFormatter())
    else:
        # Rich handler for development/CLI
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
