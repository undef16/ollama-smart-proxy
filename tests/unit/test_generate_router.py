"""Tests for the generate router functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from src.slices.generate.generate_router import GenerateRouter, GenerateRequest


class TestGenerateRouter:
    """Test the GenerateRouter class."""

    @pytest.fixture
    def mock_registry(self):
        """Mock registry fixture."""
        return MagicMock()

    @pytest.fixture
    def mock_ollama_client(self):
        """Mock Ollama client fixture."""
        return MagicMock()

    @pytest.fixture
    def generate_router(self, mock_registry, mock_ollama_client):
        """Create a GenerateRouter instance with mocks."""
        return GenerateRouter(mock_registry, mock_ollama_client)

    @pytest.mark.asyncio
    async def test_generate_success(self, generate_router):
        """Test successful generate request."""
        mock_request = GenerateRequest(model="test-model", prompt="test prompt")
        mock_response = {"response": "generated text"}

        generate_router.generate_chain.process_generate_request = AsyncMock(return_value=mock_response)

        result = await generate_router.generate(mock_request)

        generate_router.generate_chain.process_generate_request.assert_called_once_with(mock_request)
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_generate_streaming(self, generate_router):
        """Test streaming generate request."""
        mock_request = GenerateRequest(model="test-model", prompt="test prompt", stream=True)

        # Mock a generator response
        def mock_generator():
            yield {"chunk": "data1"}
            yield {"chunk": "data2"}

        mock_response = mock_generator()
        generate_router.generate_chain.process_generate_request = AsyncMock(return_value=mock_response)

        result = await generate_router.generate(mock_request)

        generate_router.generate_chain.process_generate_request.assert_called_once_with(mock_request)
        assert isinstance(result, StreamingResponse)

    @pytest.mark.asyncio
    async def test_generate_error(self, generate_router):
        """Test generate request that raises an error."""
        mock_request = GenerateRequest(model="test-model", prompt="test prompt")

        generate_router.generate_chain.process_generate_request = AsyncMock(
            side_effect=Exception("Processing error")
        )

        with pytest.raises(HTTPException) as exc_info:
            await generate_router.generate(mock_request)

        assert exc_info.value.status_code == 500
        assert "Internal server error" in exc_info.value.detail

    def test_get_router_classmethod(self, mock_registry, mock_ollama_client):
        """Test the get_router classmethod."""
        router = GenerateRouter.get_router(mock_registry, mock_ollama_client)

        assert hasattr(router, 'post')
        # Verify the router has the expected endpoint
        assert len(router.routes) > 0