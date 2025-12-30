"""Integration tests for chat slice."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from main import app


class TestChatSlice:
    """Integration tests for the chat endpoint."""

    @pytest.fixture
    def client(self):
        """Test client for the FastAPI app."""
        return TestClient(app)

    @pytest.fixture
    def mock_ollama_response(self):
        """Mock Ollama chat response."""
        return {
            "model": "qwen2.5-coder:1.5b",
            "created_at": "2023-12-01T00:00:00Z",
            "message": {
                "role": "assistant",
                "content": "Hello! How can I help you?"
            },
            "done": True
        }

    @patch('src.shared.ollama_client.OllamaClient.chat')
    @patch('src.shared.ollama_client.OllamaClient.list')
    def test_chat_endpoint_success(self, mock_list, mock_chat, client, mock_ollama_response):
        """Test successful chat request."""
        mock_chat.return_value = mock_ollama_response
        mock_list.return_value = {"models": [{"name": "qwen2.5-coder:1.5b"}]}

        request_data = {
"model": "qwen2.5-coder:1.5b",
"messages": [
                {"role": "user", "content": "Hello"}
            ]
        }

        response = client.post("/api/chat/", json=request_data)

        assert response.status_code == 200
        assert response.json() == mock_ollama_response

        mock_chat.assert_called_once_with(
            model="qwen2.5-coder:1.5b",
            messages=[{"role": "user", "content": "Hello"}],
            stream=False
        )

    @patch('src.shared.ollama_client.OllamaClient.chat')
    @patch('src.shared.ollama_client.OllamaClient.list')
    def test_chat_endpoint_with_stream(self, mock_list, mock_chat, client, mock_ollama_response):
        """Test chat request with stream=True."""
        mock_chat.return_value = mock_ollama_response
        mock_list.return_value = {"models": [{"name": "qwen2.5-coder:1.5b"}]}

        request_data = {
"model": "qwen2.5-coder:1.5b",
"messages": [
                {"role": "user", "content": "Hello"}
            ],
"stream": True
        }

        response = client.post("/api/chat/", json=request_data)

        assert response.status_code == 200

        mock_chat.assert_called_once_with(
            model="qwen2.5-coder:1.5b",
            messages=[{"role": "user", "content": "Hello"}],
            stream=True
        )

    def test_chat_endpoint_invalid_request(self, client):
        """Test chat endpoint with invalid request data."""
        request_data = {
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
            # Missing model
        }

        response = client.post("/api/chat/", json=request_data)

        assert response.status_code == 422  # Validation error