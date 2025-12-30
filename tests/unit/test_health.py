"""Unit tests for health slice."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.slices.health.health_router import HealthRouter


class TestHealthRouter:
    """Test health endpoint functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        mock_client = MagicMock()
        mock_client.list = AsyncMock(return_value={"models": []})

        router = HealthRouter(mock_client)
        result = await router.health_check()

        expected = {
            "status": "healthy",
            "proxy": "Ok",
            "upstream": "Ok"
        }
        assert result == expected
        mock_client.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_upstream_error(self):
        """Test health check when upstream Ollama is unreachable."""
        mock_client = MagicMock()
        mock_client.list = AsyncMock(side_effect=Exception("Connection failed"))

        router = HealthRouter(mock_client)
        result = await router.health_check()

        expected = {
            "status": "unhealthy",
            "proxy": "Ok",
            "upstream": "error"
        }
        assert result == expected
        mock_client.list.assert_called_once()