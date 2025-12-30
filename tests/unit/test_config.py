"""Unit tests for configuration settings."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.shared.config import Config


class TestSettings:
    """Test Settings configuration class."""

    def test_default_settings(self):
        """Test default configuration values."""
        settings = Config()
        assert settings.ollama_host == "localhost"
        assert settings.ollama_port == 11434
        assert settings.plugins_dir == Path("src/plugins")

    @patch.dict(os.environ, {"OLLAMA_PROXY_OLLAMA_HOST": "192.168.1.100"})
    def test_env_override_host(self):
        """Test overriding ollama_host via environment variable."""
        settings = Config()
        assert settings.ollama_host == "192.168.1.100"

    @patch.dict(os.environ, {"OLLAMA_PROXY_OLLAMA_PORT": "8080"})
    def test_env_override_port(self):
        """Test overriding ollama_port via environment variable."""
        settings = Config()
        assert settings.ollama_port == 8080

    @patch.dict(os.environ, {"OLLAMA_PROXY_PLUGINS_DIR": "/custom/plugins"})
    def test_env_override_plugins_dir(self):
        """Test overriding plugins_dir via environment variable."""
        settings = Config()
        assert settings.plugins_dir == Path("/custom/plugins")

    @patch.dict(os.environ, {
        "OLLAMA_PROXY_OLLAMA_HOST": "test-host",
        "OLLAMA_PROXY_OLLAMA_PORT": "9999",
        "OLLAMA_PROXY_PLUGINS_DIR": "/test/plugins"
    })
    def test_multiple_env_overrides(self):
        """Test multiple environment variable overrides."""
        settings = Config()
        assert settings.ollama_host == "test-host"
        assert settings.ollama_port == 9999
        assert settings.plugins_dir == Path("/test/plugins")