"""Unit tests for agent chain execution."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from slices.chat.agent_chain import AgentChain, ChatRequest, Message


class TestAgentChain:
    """Test agent chain execution in ChatLogic."""

    @pytest.mark.asyncio
    async def test_parse_slash_commands_single_agent(self):
        """Test parsing a single slash command from message content."""
        mock_registry = MagicMock()
        mock_ollama_client = MagicMock()
        logic = AgentChain(mock_registry, mock_ollama_client)

        content = "/example Hello world"
        cleaned_content, agents = logic._parse_slash_commands(content)

        assert cleaned_content == "Hello world"
        assert agents == {"example"}

    @pytest.mark.asyncio
    async def test_parse_slash_commands_multiple_agents(self):
        """Test parsing multiple slash commands from message content."""
        mock_registry = MagicMock()
        mock_ollama_client = MagicMock()
        logic = AgentChain(mock_registry, mock_ollama_client)

        content = "/example /rag Hello world"
        cleaned_content, agents = logic._parse_slash_commands(content)

        assert cleaned_content == "Hello world"
        assert agents == {"example", "rag"}

    @pytest.mark.asyncio
    async def test_parse_slash_commands_no_commands(self):
        """Test parsing content with no slash commands."""
        mock_registry = MagicMock()
        mock_ollama_client = MagicMock()
        logic = AgentChain(mock_registry, mock_ollama_client)

        content = "Hello world"
        cleaned_content, agents = logic._parse_slash_commands(content)

        assert cleaned_content == "Hello world"
        assert agents == set()

    @pytest.mark.asyncio
    async def test_execute_agent_chain_on_request(self):
        """Test sequential execution of on_request hooks."""
        mock_registry = MagicMock()
        mock_ollama_client = MagicMock()
        logic = AgentChain(mock_registry, mock_ollama_client)

        # Mock agents
        agent1 = MagicMock()
        agent1.on_request = AsyncMock(return_value={"modified": "by_agent1"})
        agent2 = MagicMock()
        agent2.on_request = AsyncMock(return_value={"modified": "by_agent2"})

        mock_registry.get_agent.side_effect = lambda name: {
            "agent1": agent1,
            "agent2": agent2
        }.get(name)

        context = {"original": "context"}
        result = await logic._execute_agent_chain_on_request(["agent1", "agent2"], context)

        # Verify agents were called in order
        agent1.on_request.assert_called_once_with(context)
        agent2.on_request.assert_called_once_with({"modified": "by_agent1"})

        assert result == {"modified": "by_agent2"}

    @pytest.mark.asyncio
    async def test_execute_agent_chain_on_response(self):
        """Test sequential execution of on_response hooks in reverse order."""
        mock_registry = MagicMock()
        mock_ollama_client = MagicMock()
        logic = AgentChain(mock_registry, mock_ollama_client)

        # Mock agents
        agent1 = MagicMock()
        agent1.on_response = AsyncMock(return_value={"modified": "by_agent1"})
        agent2 = MagicMock()
        agent2.on_response = AsyncMock(return_value={"modified": "by_agent2"})

        mock_registry.get_agent.side_effect = lambda name: {
            "agent1": agent1,
            "agent2": agent2
        }.get(name)

        context = {"response": {"original": "response"}}
        result = await logic._execute_agent_chain_on_response(["agent1", "agent2"], context)

        # Verify agents were called in reverse order
        agent2.on_response.assert_called_once_with({"original": "response"})
        agent1.on_response.assert_called_once_with({"modified": "by_agent2"})

        assert result == {"response": {"modified": "by_agent1"}}

    @pytest.mark.asyncio
    async def test_execute_agent_chain_missing_agent(self):
        """Test agent chain execution when an agent is not found."""
        mock_registry = MagicMock()
        mock_ollama_client = MagicMock()
        logic = AgentChain(mock_registry, mock_ollama_client)

        mock_registry.get_agent.return_value = None

        context = {"original": "context"}
        result = await logic._execute_agent_chain_on_request(["missing_agent"], context)

        # Context should remain unchanged
        assert result == context

    @pytest.mark.asyncio
    async def test_process_chat_request_with_agent(self):
        """Test processing a chat request with agent activation."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(return_value={"message": {"content": "Response"}})
        mock_client.list = AsyncMock(return_value={"models": [{"name": "test-model"}]})

        # Mock agent
        agent = MagicMock()
        agent.on_request = AsyncMock(return_value={
            "model": "test-model",
            "messages": [{"role": "user", "content": "Modified: Hello"}],
            "stream": False,
            "agents": ["example"]
        })
        agent.on_response = AsyncMock(return_value={
            "message": {"content": "Modified: Response"}
        })

        mock_registry = MagicMock()
        mock_registry.get_agent.return_value = agent

        logic = AgentChain(mock_registry, mock_client)
        chat_request = ChatRequest(
            model="test-model",
            messages=[Message(role="user", content="/example Hello")]
        )

        response = await logic.process_chat_request(chat_request)

        # Verify agent was called
        agent.on_request.assert_called_once()
        agent.on_response.assert_called_once()

        # Verify Ollama was called with modified context
        mock_client.chat.assert_called_once_with(
            model="test-model",
            messages=[{"role": "user", "content": "Modified: Hello"}],
            stream=False
        )

        assert response == {"message": {"content": "Modified: Response"}}