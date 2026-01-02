"""Unit tests for Ollama client wrapper."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.shared.ollama_client import OllamaClient
from ..test_const import TEST_MODEL, TEST_PROMPT, MOCK_CHAT_RESPONSE, MOCK_GENERATE_RESPONSE, MOCK_PULL_RESPONSE, MOCK_SHOW_RESPONSE, MOCK_DELETE_RESPONSE, MOCK_EMBEDDINGS_RESPONSE


class TestOllamaClient:
    """Test OllamaClient async wrapper."""

    def test_init(self):
        """Test OllamaClient initialization."""
        client = OllamaClient()
        assert hasattr(client, '_client')
        assert client._client is not None

    @pytest.mark.asyncio
    async def test_chat(self, mock_ollama):
        """Test chat method."""
        mock_client = MagicMock()
        mock_ollama.Client.return_value = mock_client
        mock_client.chat.return_value = MOCK_CHAT_RESPONSE

        client = OllamaClient()
        result = await client.chat(
            model=TEST_MODEL,
            messages=[{"role": "user", "content": "Hello"}],
            stream=False
        )

        assert result == MOCK_CHAT_RESPONSE
        mock_client.chat.assert_called_once_with(
            model=TEST_MODEL,
            messages=[{"role": "user", "content": "Hello"}],
            stream=False
        )

    @pytest.mark.asyncio
    async def test_generate(self, mock_ollama):
        """Test generate method."""
        mock_client = MagicMock()
        mock_ollama.Client.return_value = mock_client
        mock_client.generate.return_value = MOCK_GENERATE_RESPONSE

        client = OllamaClient()
        result = await client.generate(
            model=TEST_MODEL,
            prompt=TEST_PROMPT,
            stream=True
        )

        assert result == MOCK_GENERATE_RESPONSE
        mock_client.generate.assert_called_once_with(
            model=TEST_MODEL,
            prompt=TEST_PROMPT,
            stream=True
        )

    @pytest.mark.asyncio
    async def test_pull(self, mock_ollama):
        """Test pull method."""
        mock_client = MagicMock()
        mock_ollama.Client.return_value = mock_client
        mock_client.pull.return_value = MOCK_PULL_RESPONSE

        client = OllamaClient()
        result = await client.pull(TEST_MODEL)

        assert result == MOCK_PULL_RESPONSE
        mock_client.pull.assert_called_once_with(TEST_MODEL)

    @pytest.mark.asyncio
    async def test_list(self, mock_ollama):
        """Test list method."""
        mock_client = MagicMock()
        mock_ollama.Client.return_value = mock_client
        mock_client.list.return_value = {"models": []}

        client = OllamaClient()
        result = await client.list()

        assert result == {"models": []}
        mock_client.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_show(self, mock_ollama):
        """Test show method."""
        mock_client = MagicMock()
        mock_ollama.Client.return_value = mock_client
        mock_client.show.return_value = MOCK_SHOW_RESPONSE

        client = OllamaClient()
        result = await client.show(TEST_MODEL)

        assert result == MOCK_SHOW_RESPONSE
        mock_client.show.assert_called_once_with(TEST_MODEL)

    @pytest.mark.asyncio
    async def test_delete(self, mock_ollama):
        """Test delete method."""
        mock_client = MagicMock()
        mock_ollama.Client.return_value = mock_client
        mock_client.delete.return_value = MOCK_DELETE_RESPONSE

        client = OllamaClient()
        result = await client.delete(TEST_MODEL)

        assert result == MOCK_DELETE_RESPONSE
        mock_client.delete.assert_called_once_with(TEST_MODEL)

    @pytest.mark.asyncio
    async def test_embeddings(self, mock_ollama):
        """Test embeddings method."""
        mock_client = MagicMock()
        mock_ollama.Client.return_value = mock_client
        mock_client.embeddings.return_value = MOCK_EMBEDDINGS_RESPONSE

        client = OllamaClient()
        result = await client.embeddings(
            model=TEST_MODEL,
            prompt=TEST_PROMPT
        )

        assert result == MOCK_EMBEDDINGS_RESPONSE
        mock_client.embeddings.assert_called_once_with(
            model=TEST_MODEL,
            prompt=TEST_PROMPT
        )