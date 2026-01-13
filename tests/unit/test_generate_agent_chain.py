"""Tests for the generate agent chain functionality."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import time
from fastapi.responses import StreamingResponse

from slices.generate.generate_agent_chain import GenerateAgentChain
from ..test_const import TEST_MODEL, TEST_PROMPT, MOCK_CHAT_RESPONSE, FALSE_VALUE, TRUE_VALUE


class TestGenerateAgentChain:
    """Test the GenerateAgentChain class."""

    @pytest.fixture
    def generate_chain(self, mock_registry):
        """Create a GenerateAgentChain instance with mocks."""
        return GenerateAgentChain(mock_registry)

    def test_init(self, mock_registry):
        """Test GenerateAgentChain initialization."""
        chain = GenerateAgentChain(mock_registry)
        assert chain.registry == mock_registry
        assert chain._model_cache is None

    def test_parse_slash_commands_no_agents(self, generate_chain):
        """Test parsing slash commands when there are none."""
        content = "This is a normal prompt without agents"
        cleaned_content, agents = generate_chain._parse_slash_commands(content)
        assert cleaned_content == "This is a normal prompt without agents"
        assert agents == set()

    def test_parse_slash_commands_with_agents(self, generate_chain):
        """Test parsing slash commands with agents."""
        content = "/example /test This is a prompt with agents"
        cleaned_content, agents = generate_chain._parse_slash_commands(content)
        assert cleaned_content == "This is a prompt with agents"
        assert agents == {"example", "test"}

    @pytest.mark.asyncio
    async def test_execute_agent_chain_on_request_no_agents(self, generate_chain):
        """Test executing agent chain on request with no agents."""
        context = {"model": TEST_MODEL, "prompt": TEST_PROMPT}
        result = await generate_chain._execute_agent_chain_on_request([], context)
        assert result == context

    @pytest.mark.asyncio
    async def test_execute_agent_chain_on_request_with_agents(self, generate_chain):
        """Test executing agent chain on request with agents."""
        mock_agent = AsyncMock()
        mock_agent.on_request = AsyncMock(return_value={"model": "modified-model", "prompt": "modified prompt"})
        
        generate_chain.registry.get_agent.return_value = mock_agent
        
        context = {"model": TEST_MODEL, "prompt": TEST_PROMPT}
        result = await generate_chain._execute_agent_chain_on_request(["test-agent"], context)
        
        generate_chain.registry.get_agent.assert_called_once_with("test-agent")
        mock_agent.on_request.assert_called_once_with(context)
        assert result == {"model": "modified-model", "prompt": "modified prompt"}

    @pytest.mark.asyncio
    async def test_execute_agent_chain_on_request_missing_agent(self, generate_chain):
        """Test executing agent chain on request with missing agent."""
        generate_chain.registry.get_agent.return_value = None
        
        context = {"model": TEST_MODEL, "prompt": TEST_PROMPT}
        result = await generate_chain._execute_agent_chain_on_request(["missing-agent"], context)
        
        generate_chain.registry.get_agent.assert_called_once_with("missing-agent")
        assert result == context

    @pytest.mark.asyncio
    async def test_execute_agent_chain_on_response_no_agents(self, generate_chain):
        """Test executing agent chain on response with no agents."""
        context = {"response": {"content": "test response"}}
        result = await generate_chain._execute_agent_chain_on_response([], {"original": "request"}, context)
        assert result == context

    @pytest.mark.asyncio
    async def test_execute_agent_chain_on_response_with_agents(self, generate_chain):
        """Test executing agent chain on response with agents."""
        mock_agent = AsyncMock()
        mock_agent.on_response = AsyncMock(return_value={"content": "modified response"})
        
        generate_chain.registry.get_agent.return_value = mock_agent
        
        context = {"response": {"content": "test response"}}
        result = await generate_chain._execute_agent_chain_on_response(["test-agent"], {"original": "request"}, context)

        generate_chain.registry.get_agent.assert_called_once_with("test-agent")
        mock_agent.on_response.assert_called_once_with({"original": "request"}, {"content": "test response"})
        assert result == {"response": {"content": "modified response"}}

    @pytest.mark.asyncio
    async def test_process_request_basic(self, generate_chain):
        """Test processing a basic generate request."""
        request_dict = {"model": TEST_MODEL, "prompt": TEST_PROMPT}
        mock_response = {"response": "generated text"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_client.post = AsyncMock(return_value=mock_resp)

            result = await generate_chain.process_request(request_dict)

        assert result == mock_response

    @pytest.mark.asyncio
    async def test_process_request_with_agents(self, generate_chain):
        """Test processing a generate request with agents."""
        request_dict = {"model": TEST_MODEL, "prompt": "/example test prompt"}
        mock_response = {"response": "generated text"}
        mock_agent = AsyncMock()

        generate_chain.registry.get_agent.return_value = mock_agent
        mock_agent.on_request = AsyncMock(return_value={
            "model": TEST_MODEL,
            "prompt": TEST_PROMPT,
            "stream": False,
            "agents": ["example"]
        })
        mock_agent.on_response = AsyncMock(return_value={"response": "generated text [processed by example agent]"})

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_client.post = AsyncMock(return_value=mock_resp)

            result = await generate_chain.process_request(request_dict)

        assert result == {"response": "generated text [processed by example agent]"}

    @pytest.mark.asyncio
    async def test_process_request_streaming(self, generate_chain):
        """Test processing a streaming generate request."""
        request_dict = {"model": TEST_MODEL, "prompt": TEST_PROMPT, "stream": True}

        async def async_iter():
            yield b'{"response": "chunk"}'

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_resp = MagicMock()
            mock_resp.aiter_bytes = MagicMock(return_value=async_iter())
            mock_resp.status_code = 200
            mock_resp.headers = {}
            mock_client.post = AsyncMock(return_value=mock_resp)

            result = await generate_chain.process_request(request_dict)

        assert isinstance(result, StreamingResponse)

    @pytest.mark.asyncio
    async def test_process_request_error(self, generate_chain):
        """Test processing a generate request that raises an error."""
        request_dict = {"model": TEST_MODEL, "prompt": TEST_PROMPT}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(side_effect=Exception("API Error"))

            with pytest.raises(Exception, match="API Error"):
                await generate_chain.process_request(request_dict)

