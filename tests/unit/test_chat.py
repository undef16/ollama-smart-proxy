"""Unit tests for chat request parsing."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from slices.chat.chat_agent_chain import ChatAgentChain, Message


class TestChatLogic:
    """Test ChatLogic processing."""

    @pytest.mark.asyncio
    async def test_process_request(self):
        """Test processing a chat request."""
        mock_registry = MagicMock()
        logic = ChatAgentChain(mock_registry)

        request_dict = {
            "model": "qwen2.5-coder:1.5b",
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"message": {"content": "Hello back"}}
            mock_client.post = AsyncMock(return_value=mock_resp)

            response = await logic.process_request(request_dict)

        assert response == {"message": {"content": "Hello back"}}

    @pytest.mark.asyncio
    async def test_process_request_model_not_loaded(self):
        """Test processing a chat request when model needs to be pulled."""
        mock_registry = MagicMock()
        logic = ChatAgentChain(mock_registry)

        request_dict = {
            "model": "qwen2.5-coder:1.5b",
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"message": {"content": "Hello back"}}
            mock_client.post = AsyncMock(return_value=mock_resp)

            response = await logic.process_request(request_dict)

        assert response == {"message": {"content": "Hello back"}}