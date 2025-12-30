"""Unit tests for plugin registry."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.shared.plugin_registry import PluginRegistry


class TestPluginRegistry:
    """Test PluginRegistry functionality."""

    @patch('src.shared.plugin_registry.Config')
    def test_init_no_plugins_dir(self, mock_settings_class):
        """Test initialization when plugins directory doesn't exist."""
        mock_settings = MagicMock()
        mock_settings.plugins_dir.exists.return_value = False
        mock_settings_class.return_value = mock_settings

        PluginRegistry._instance = None
        registry = PluginRegistry()
        assert registry._agents == {}

    @patch('src.shared.plugin_registry.Config')
    def test_init_empty_plugins_dir(self, mock_settings_class):
        """Test initialization with empty plugins directory."""
        mock_settings = MagicMock()
        mock_settings.plugins_dir.exists.return_value = True
        mock_settings.plugins_dir.iterdir.return_value = []
        mock_settings_class.return_value = mock_settings

        PluginRegistry._instance = None
        registry = PluginRegistry()
        assert registry._agents == {}


    @patch('src.shared.plugin_registry.Config')
    def test_get_agent_existing(self, mock_settings_class):
        """Test getting an existing agent."""
        mock_settings = MagicMock()
        mock_settings.plugins_dir.exists.return_value = False
        mock_settings_class.return_value = mock_settings
        registry = PluginRegistry()

        mock_agent = MagicMock()
        registry._agents["test"] = mock_agent

        assert registry.get_agent("test") == mock_agent

    @patch('src.shared.plugin_registry.Config')
    def test_get_agent_nonexistent(self, mock_settings_class):
        """Test getting a nonexistent agent."""
        mock_settings = MagicMock()
        mock_settings.plugins_dir.exists.return_value = False
        mock_settings_class.return_value = mock_settings
        registry = PluginRegistry()

        assert registry.get_agent("nonexistent") is None

    @patch('src.shared.plugin_registry.Config')
    def test_agents_property(self, mock_settings_class):
        """Test agents property returns copy."""
        mock_settings = MagicMock()
        mock_settings.plugins_dir.exists.return_value = False
        mock_settings_class.return_value = mock_settings
        registry = PluginRegistry()

        registry._agents = {"agent1": MagicMock(), "agent2": MagicMock()}
        agents = registry.agents

        assert agents == registry._agents
        assert agents is not registry._agents  # Should be a copy