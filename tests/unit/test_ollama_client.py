"""Unit tests for Ollama client wrapper."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.shared.ollama_client import OllamaClient


class TestOllamaClient:
    """Test OllamaClient async wrapper."""

    def test_init(self):
        """Test OllamaClient initialization."""
        client = OllamaClient()
        assert hasattr(client, '_client')
        assert client._client is not None

    @pytest.mark.asyncio
    @patch('src.shared.ollama_client.ollama')
    async def test_chat(self, mock_ollama):
        """Test chat method."""
        mock_client = MagicMock()
        mock_ollama.Client.return_value = mock_client
        mock_client.chat.return_value = {"response": "test"}

        client = OllamaClient()
        result = await client.chat(
            model="test-model",
            messages=[{"role": "user", "content": "Hello"}],
            stream=False
        )

        assert result == {"response": "test"}
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=[{"role": "user", "content": "Hello"}],
            stream=False
        )

    @pytest.mark.asyncio
    @patch('src.shared.ollama_client.ollama')
    async def test_generate(self, mock_ollama):
        """Test generate method."""
        mock_client = MagicMock()
        mock_ollama.Client.return_value = mock_client
        mock_client.generate.return_value = {"response": "generated text"}

        client = OllamaClient()
        result = await client.generate(
            model="test-model",
            prompt="Test prompt",
            stream=True
        )

        assert result == {"response": "generated text"}
        mock_client.generate.assert_called_once_with(
            model="test-model",
            prompt="Test prompt",
            stream=True
        )

    @pytest.mark.asyncio
    @patch('src.shared.ollama_client.ollama')
    async def test_pull(self, mock_ollama):
        """Test pull method."""
        mock_client = MagicMock()
        mock_ollama.Client.return_value = mock_client
        mock_client.pull.return_value = {"status": "pulled"}

        client = OllamaClient()
        result = await client.pull("test-model")

        assert result == {"status": "pulled"}
        mock_client.pull.assert_called_once_with("test-model")

    @pytest.mark.asyncio
    @patch('src.shared.ollama_client.ollama')
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
    @patch('src.shared.ollama_client.ollama')
    async def test_show(self, mock_ollama):
        """Test show method."""
        mock_client = MagicMock()
        mock_ollama.Client.return_value = mock_client
        mock_client.show.return_value = {"info": "model info"}

        client = OllamaClient()
        result = await client.show("test-model")

        assert result == {"info": "model info"}
        mock_client.show.assert_called_once_with("test-model")

    @pytest.mark.asyncio
    @patch('src.shared.ollama_client.ollama')
    async def test_delete(self, mock_ollama):
        """Test delete method."""
        mock_client = MagicMock()
        mock_ollama.Client.return_value = mock_client
        mock_client.delete.return_value = {"status": "deleted"}

        client = OllamaClient()
        result = await client.delete("test-model")

        assert result == {"status": "deleted"}
        mock_client.delete.assert_called_once_with("test-model")

    @pytest.mark.asyncio
    @patch('src.shared.ollama_client.ollama')
    async def test_embeddings(self, mock_ollama):
        """Test embeddings method."""
        mock_client = MagicMock()
        mock_ollama.Client.return_value = mock_client
        mock_client.embeddings.return_value = {"embeddings": [0.1, 0.2]}

        client = OllamaClient()
        result = await client.embeddings(
            model="test-model",
            prompt="test prompt"
        )

        assert result == {"embeddings": [0.1, 0.2]}
        mock_client.embeddings.assert_called_once_with(
            model="test-model",
            prompt="test prompt"
        )