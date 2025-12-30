"""Unit tests for plugins slice."""

from unittest.mock import MagicMock, patch

import pytest

from src.slices.plugins.plugins_router import PluginsRouter


class TestPluginsRouter:
    """Test plugins endpoint functionality."""

    @pytest.mark.asyncio
    async def test_list_plugins(self):
        """Test list_plugins endpoint."""
        # Mock agents
        mock_agent1 = MagicMock()
        mock_agent1.name = "agent1"
        mock_agent2 = MagicMock()
        mock_agent2.name = "agent2"

        mock_registry = MagicMock()
        mock_registry.agents = {
            "agent1": mock_agent1,
            "agent2": mock_agent2
        }

        router = PluginsRouter(mock_registry)
        result = await router.list_plugins()

        expected = [
            {"name": "agent1", "status": "loaded"},
            {"name": "agent2", "status": "loaded"}
        ]
        assert result == expected

    @pytest.mark.asyncio
    async def test_list_plugins_empty(self):
        """Test list_plugins endpoint with no plugins."""
        mock_registry = MagicMock()
        mock_registry.agents = {}

        router = PluginsRouter(mock_registry)
        result = await router.list_plugins()

        assert result == []