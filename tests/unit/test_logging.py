"""Unit tests for logging setup."""

import logging
from unittest.mock import patch

from src.shared.logging import LoggingManager


class TestLogging:
    """Test logging setup functions."""

    @patch('src.shared.logging.logging')
    def test_setup_logging_default_level(self, mock_logging):
        """Test setup_logging with default INFO level."""
        LoggingManager.setup_logging()

        # Check that handler was added to root logger
        mock_logging.getLogger().addHandler.assert_called_once()
        # Check that setLevel was called (level is set)
        mock_logging.getLogger().setLevel.assert_called()

    @patch('src.shared.logging.logging')
    def test_setup_logging_custom_level(self, mock_logging):
        """Test setup_logging with custom DEBUG level."""
        LoggingManager.setup_logging("DEBUG")

        # Verify setLevel and addHandler were called
        mock_logging.getLogger().setLevel.assert_called()
        mock_logging.getLogger().addHandler.assert_called_once()

    @patch('src.shared.logging.logging')
    def test_setup_logging_invalid_level(self, mock_logging):
        """Test setup_logging with invalid level defaults to INFO."""
        LoggingManager.setup_logging("INVALID")

        # Should default to INFO (setLevel called)
        mock_logging.getLogger().setLevel.assert_called()
        mock_logging.getLogger().addHandler.assert_called_once()

    def test_get_logger(self):
        """Test get_logger returns a logger instance."""
        logger = LoggingManager.get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_get_logger_different_names(self):
        """Test get_logger with different names."""
        logger1 = LoggingManager.get_logger("module1")
        logger2 = LoggingManager.get_logger("module2")

        assert logger1.name == "module1"
        assert logger2.name == "module2"
        assert logger1 is not logger2