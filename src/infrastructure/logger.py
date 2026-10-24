"""Logging configuration"""

import logging
import sys
from pathlib import Path

from ..domain.models import AppConfig


def setup_logging(config: AppConfig | None = None, log_file: Path | None = None) -> logging.Logger:
    """Configure application logging"""
    logger = logging.getLogger("file_organizer")
    logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler with color support
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get logger instance for a module"""
    return logging.getLogger(f"file_organizer.{name}")


class LogCapture:
    """Capture log records for TUI display"""

    def __init__(self, max_records: int = 1000):
        self.max_records = max_records
        self.records: list[logging.LogRecord] = []
        self._handler: logging.Handler | None = None

    def install(self, logger: logging.Logger) -> None:
        """Install capture handler on logger"""
        self._handler = logging.Handler()
        self._handler.setLevel(logging.DEBUG)
        self._handler.emit = self._emit
        logger.addHandler(self._handler)

    def uninstall(self, logger: logging.Logger) -> None:
        """Remove capture handler"""
        if self._handler:
            logger.removeHandler(self._handler)
            self._handler = None

    def _emit(self, record: logging.LogRecord) -> None:
        """Store log record"""
        self.records.append(record)
        if len(self.records) > self.max_records:
            self.records.pop(0)

    def get_recent(self, count: int = 100, level: int | None = None) -> list[logging.LogRecord]:
        """Get recent log records, optionally filtered by level"""
        records = self.records
        if level is not None:
            records = [r for r in records if r.levelno >= level]
        return records[-count:]

    def clear(self) -> None:
        """Clear captured records"""
        self.records.clear()