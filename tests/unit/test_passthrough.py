"""Unit tests for passthrough slice."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from src.slices.passthrough.passthrough_router import PassthroughRouter


class TestPassthroughRouter:
    """Test passthrough endpoint functionality."""

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test generate endpoint with valid request."""
        mock_client = MagicMock()
        mock_client.generate = AsyncMock(return_value={"response": "generated text"})

        request = {
            "model": "test-model",
            "prompt": "Test prompt",
            "stream": True,
            "temperature": 0.7
        }

        router = PassthroughRouter(mock_client)
        result = await router.generate(request)

        assert result == {"response": "generated text"}
        mock_client.generate.assert_called_once_with(
            model="test-model",
            prompt="Test prompt",
            stream=True,
            temperature=0.7
        )

    @pytest.mark.asyncio
    async def test_generate_missing_model(self):
        """Test generate endpoint with missing model."""
        request = {
            "prompt": "Test prompt"
        }

        mock_client = MagicMock()
        router = PassthroughRouter(mock_client)
        with pytest.raises(HTTPException) as exc_info:
            await router.generate(request)
        assert exc_info.value.detail == "model is required"

    @pytest.mark.asyncio
    async def test_generate_missing_prompt(self):
        """Test generate endpoint with missing prompt."""
        request = {
            "model": "test-model"
        }

        mock_client = MagicMock()
        router = PassthroughRouter(mock_client)
        with pytest.raises(HTTPException) as exc_info:
            await router.generate(request)
        assert exc_info.value.detail == "prompt is required"

    @pytest.mark.asyncio
    async def test_generic_passthrough(self):
        """Test generic passthrough endpoint."""
        with patch('httpx.AsyncClient') as mock_client_class, \
             patch('src.shared.config.Config') as mock_settings_class:

            mock_settings = MagicMock()
            mock_settings.ollama_host = 'localhost'
            mock_settings.ollama_port = 11434
            mock_settings_class.return_value = mock_settings

            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/json'}
            mock_response.aiter_bytes = AsyncMock(return_value=b'{"test": "data"}')
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_request = MagicMock()
            mock_request.method = 'POST'
            mock_request.headers = {'content-type': 'application/json', 'authorization': 'Bearer token'}
            mock_request.body = AsyncMock(return_value=b'{"key": "value"}')
            mock_request.json = AsyncMock(return_value={"key": "value"})

            router = PassthroughRouter(MagicMock())
            result = await router.generic_passthrough(mock_request, "chat")

            assert isinstance(result, StreamingResponse)
            assert result.status_code == 200

            mock_client.request.assert_called_once_with(
                'POST',
                'http://localhost:11434/api/chat',
                json={"key": "value"},
                headers={'content-type': 'application/json', 'authorization': 'Bearer token'},
                content=None
            )