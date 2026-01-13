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

    @patch('httpx.AsyncClient')
    def test_chat_endpoint_success(self, mock_client_class, client, mock_ollama_response):
        """Test successful chat request."""
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_ollama_response
        mock_client.post = AsyncMock(return_value=mock_resp)

        request_data = {
            "model": "qwen2.5-coder:1.5b",
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }

        response = client.post("/api/chat", json=request_data)

        assert response.status_code == 200
        assert response.json() == mock_ollama_response

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[1]["json"] == {
            'model': 'qwen2.5-coder:1.5b',
            'messages': [{'role': 'user', 'content': 'Hello'}],
            'stream': False
        }

    @patch('httpx.AsyncClient')
    def test_chat_endpoint_with_stream(self, mock_client_class, client, mock_ollama_response):
        """Test chat request with stream=True."""
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {}
        mock_resp.aiter_bytes.return_value = iter([b"data"])
        mock_client.post = AsyncMock(return_value=mock_resp)

        request_data = {
            "model": "qwen2.5-coder:1.5b",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "stream": True
        }

        response = client.post("/api/chat", json=request_data)

        # For streaming, we get a StreamingResponse which TestClient handles
        assert response.status_code == 200

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[1]["json"] == {
            'model': 'qwen2.5-coder:1.5b',
            'messages': [{'role': 'user', 'content': 'Hello'}],
            'stream': True
        }

    def test_chat_endpoint_invalid_request(self, client):
        """Test chat endpoint with invalid request data."""
        request_data = {
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
            # Missing model
        }

        response = client.post("/api/chat", json=request_data)

        assert response.status_code == 500  # Internal server error due to missing validation