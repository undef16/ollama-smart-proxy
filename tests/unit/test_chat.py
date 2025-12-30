"""Unit tests for chat request parsing."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from slices.chat.agent_chain import AgentChain, ChatRequest, Message


class TestChatRequest:
    """Test ChatRequest model parsing."""

    def test_valid_request_parsing(self):
        """Test parsing a valid chat request."""
        data = {
            "model": "qwen2.5-coder:1.5b",
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }
        request = ChatRequest(**data)
        assert request.model == "qwen2.5-coder:1.5b"
        assert len(request.messages) == 1
        assert request.messages[0].role == "user"
        assert request.messages[0].content == "Hello"
        assert request.stream is False

    def test_request_with_stream(self):
        """Test parsing request with stream=True."""
        data = {
            "model": "qwen2.5-coder:1.5b",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "stream": True
        }
        request = ChatRequest(**data)
        assert request.stream is True

    def test_invalid_request_missing_model(self):
        """Test parsing fails with missing model."""
        data = {
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }
        with pytest.raises(ValidationError):
            ChatRequest(**data)

    def test_invalid_request_missing_messages(self):
        """Test parsing fails with missing messages."""
        data = {
            "model": "qwen2.5-coder:1.5b"
        }
        with pytest.raises(ValidationError):
            ChatRequest(**data)


class TestChatLogic:
    """Test ChatLogic processing."""

    @pytest.mark.asyncio
    async def test_process_chat_request(self):
        """Test processing a chat request."""
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(return_value={"response": "Hello back"})
        mock_client.list = AsyncMock(return_value={"models": [{"name": "qwen2.5-coder:1.5b"}]})
        mock_registry = MagicMock()
        logic = AgentChain(mock_registry, mock_client)

        chat_request = ChatRequest(
            model="qwen2.5-coder:1.5b",
            messages=[
                Message(role="user", content="Hello")
            ]
        )

        response = await logic.process_chat_request(chat_request)

        assert response == {"response": "Hello back"}
        mock_client.chat.assert_called_once_with(
            model="qwen2.5-coder:1.5b",
            messages=[{"role": "user", "content": "Hello"}],
            stream=False
        )

    @pytest.mark.asyncio
    async def test_process_chat_request_with_stream(self):
        """Test processing a chat request with stream."""
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(return_value={"response": "Hello back"})
        mock_client.list = AsyncMock(return_value={"models": [{"name": "qwen2.5-coder:1.5b"}]})
        mock_registry = MagicMock()
        logic = AgentChain(mock_registry, mock_client)

        chat_request = ChatRequest(
            model="qwen2.5-coder:1.5b",
            messages=[
                Message(role="user", content="Hello")
            ],
            stream=True
        )

        response = await logic.process_chat_request(chat_request)

        mock_client.chat.assert_called_once_with(
            model="qwen2.5-coder:1.5b",
            messages=[{"role": "user", "content": "Hello"}],
            stream=True
        )

    @pytest.mark.asyncio
    async def test_process_chat_request_model_not_loaded(self):
        """Test processing a chat request when model needs to be pulled."""
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(return_value={"response": "Hello back"})
        mock_client.list = AsyncMock(return_value={"models": [{"name": "other-model"}]})
        mock_client.pull = AsyncMock()
        mock_registry = MagicMock()
        logic = AgentChain(mock_registry, mock_client)

        chat_request = ChatRequest(
            model="qwen2.5-coder:1.5b",
            messages=[
                Message(role="user", content="Hello")
            ]
        )

        response = await logic.process_chat_request(chat_request)

        assert response == {"response": "Hello back"}
        mock_client.chat.assert_called_once_with(
            model="qwen2.5-coder:1.5b",
            messages=[{"role": "user", "content": "Hello"}],
            stream=False
        )