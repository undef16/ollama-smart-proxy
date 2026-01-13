"""Unit tests for passthrough slice."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import StreamingResponse, Response

from src.slices.passthrough.passthrough_router import PassthroughRouter


class TestPassthroughRouter:
    """Test passthrough endpoint functionality."""


    @pytest.mark.asyncio
    async def test_generic_passthrough(self):
        """Test generic passthrough endpoint."""
        with patch('httpx.Client') as mock_client_class, \
             patch('src.shared.config.Config') as mock_settings_class:

            mock_settings = MagicMock()
            mock_settings.ollama_host = 'localhost'
            mock_settings.ollama_port = 11434
            mock_settings_class.return_value = mock_settings

            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/json'}
            mock_response.content = b'{"test": "data"}'
            mock_client.request = MagicMock(return_value=mock_response)
            mock_client_class.return_value.__enter__.return_value = mock_client

            async def mock_body():
                return b'{"key": "value"}'

            mock_request = MagicMock()
            mock_request.method = 'POST'
            mock_request.headers = {'content-type': 'application/json', 'authorization': 'Bearer token'}
            mock_request.body = mock_body

            router = PassthroughRouter()
            result = router.generic_passthrough(mock_request, "chat")

            assert result.status_code == 200
            assert result.body == b'{"test": "data"}'

            mock_client.request.assert_called_once_with(
                'POST',
                'http://localhost:11434/api/chat',
                headers={'content-type': 'application/json', 'authorization': 'Bearer token'},
                json=None,
                content=b''
            )