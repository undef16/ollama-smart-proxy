import logging
import sys
from typing import Optional

from .config import Config
from src.const import LOG_FORMAT, LOG_DATE_FORMAT


class LoggingManager:
    """Manager for logging setup and logger retrieval."""

    @classmethod
    def setup_logging(cls, level: str = "INFO") -> None:
        """Setup structured logging for the application.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        # Convert string level to logging level
        numeric_level = getattr(logging, level.upper(), logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            fmt=LOG_FORMAT,
            datefmt=LOG_DATE_FORMAT
        )

        # Setup console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(numeric_level)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        root_logger.addHandler(console_handler)

        # Set levels for noisy libraries
        config = Config()
        for logger_name, level in config.library_log_levels.items():
            logging.getLogger(logger_name).setLevel(getattr(logging, level.upper(), logging.WARNING))

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a logger instance.

        Args:
            name: Logger name, typically __name__

        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)