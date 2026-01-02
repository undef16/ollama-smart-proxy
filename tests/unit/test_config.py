"""Unit tests for configuration settings."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.shared.config import Config
from ..test_const import TEST_HOST, TEST_PORT, TEST_HOST_OVERRIDE, TEST_PORT_OVERRIDE, TEST_PORT_OVERRIDE_2, PLUGINS_DIR_PATH, TEST_PLUGINS_DIR_PATH


class TestSettings:
    """Test Settings configuration class."""

    @patch('src.shared.config.Config.load_config_from_json', return_value={})
    def test_default_settings(self, mock_load):
        """Test default configuration values."""
        settings = Config()
        assert settings.ollama_host == TEST_HOST
        assert settings.ollama_port == TEST_PORT
        assert settings.plugins_dir == Path(PLUGINS_DIR_PATH)

    @patch.dict(os.environ, {"OLLAMA_PROXY_OLLAMA_HOST": "192.168.1.100"})
    def test_env_override_host(self):
        """Test overriding ollama_host via environment variable."""
        settings = Config()
        assert settings.ollama_host == "192.168.1.100"

    @patch.dict(os.environ, {"OLLAMA_PROXY_OLLAMA_PORT": str(TEST_PORT_OVERRIDE_2)})
    def test_env_override_port(self):
        """Test overriding ollama_port via environment variable."""
        settings = Config()
        assert settings.ollama_port == TEST_PORT_OVERRIDE_2

    @patch.dict(os.environ, {"OLLAMA_PROXY_PLUGINS_DIR": "/custom/plugins"})
    def test_env_override_plugins_dir(self):
        """Test overriding plugins_dir via environment variable."""
        settings = Config()
        assert settings.plugins_dir == Path("/custom/plugins")

    @patch.dict(os.environ, {
        "OLLAMA_PROXY_OLLAMA_HOST": TEST_HOST_OVERRIDE,
        "OLLAMA_PROXY_OLLAMA_PORT": str(TEST_PORT_OVERRIDE),
        "OLLAMA_PROXY_PLUGINS_DIR": TEST_PLUGINS_DIR_PATH
    })
    def test_multiple_env_overrides(self):
        """Test multiple environment variable overrides."""
        settings = Config()
        assert settings.ollama_host == TEST_HOST_OVERRIDE
        assert settings.ollama_port == TEST_PORT_OVERRIDE
        assert settings.plugins_dir == Path(TEST_PLUGINS_DIR_PATH)