"""Tests for the generate agent chain functionality."""

import pytest
from unittest.mock import AsyncMock
import time

from src.slices.generate.agent_chain import GenerateChain, GenerateRequest
from ..test_const import TEST_MODEL, TEST_PROMPT, MOCK_CHAT_RESPONSE, FALSE_VALUE, TRUE_VALUE


class TestGenerateRequest:
    """Test the GenerateRequest model."""

    def test_generate_request_defaults(self):
        """Test GenerateRequest with default values."""
        request = GenerateRequest(model=TEST_MODEL, prompt=TEST_PROMPT)
        assert request.model == TEST_MODEL
        assert request.prompt == TEST_PROMPT
        assert request.stream is FALSE_VALUE

    def test_generate_request_with_stream(self):
        """Test GenerateRequest with stream=True."""
        request = GenerateRequest(model=TEST_MODEL, prompt=TEST_PROMPT, stream=TRUE_VALUE)
        assert request.model == TEST_MODEL
        assert request.prompt == TEST_PROMPT
        assert request.stream is TRUE_VALUE


class TestGenerateChain:
    """Test the GenerateChain class."""

    @pytest.fixture
    def generate_chain(self, mock_registry, mock_ollama_client):
        """Create a GenerateChain instance with mocks."""
        return GenerateChain(mock_registry, mock_ollama_client)

    def test_init(self, mock_registry, mock_ollama_client):
        """Test GenerateChain initialization."""
        chain = GenerateChain(mock_registry, mock_ollama_client)
        assert chain.registry == mock_registry
        assert chain.ollama_client == mock_ollama_client
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
    async def test_process_generate_request_basic(self, generate_chain):
        """Test processing a basic generate request."""
        mock_request = GenerateRequest(model=TEST_MODEL, prompt=TEST_PROMPT)
        mock_response = {"response": "generated text"}
        
        generate_chain.ollama_client.generate = AsyncMock(return_value=mock_response)
        
        result = await generate_chain.process_generate_request(mock_request)
        
        generate_chain.ollama_client.generate.assert_called_once_with(
            model=TEST_MODEL,
            prompt=TEST_PROMPT,
            stream=FALSE_VALUE
        )
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_process_generate_request_with_agents(self, generate_chain):
        """Test processing a generate request with agents."""
        mock_request = GenerateRequest(model=TEST_MODEL, prompt="/example test prompt")
        mock_response = {"response": "generated text"}
        mock_agent = AsyncMock()
        
        generate_chain.ollama_client.generate = AsyncMock(return_value=mock_response)
        generate_chain.registry.get_agent.return_value = mock_agent
        mock_agent.on_request = AsyncMock(return_value={
            "model": TEST_MODEL,
            "prompt": TEST_PROMPT,
            "stream": FALSE_VALUE,
            "agents": ["example"]
        })
        mock_agent.on_response = AsyncMock(return_value={"response": "generated text [processed by example agent]"})
        
        result = await generate_chain.process_generate_request(mock_request)
        
        generate_chain.ollama_client.generate.assert_called_once_with(
            model=TEST_MODEL,
            prompt=TEST_PROMPT,
            stream=FALSE_VALUE
        )
        assert result == {"response": "generated text [processed by example agent]"}

    @pytest.mark.asyncio
    async def test_process_generate_request_streaming(self, generate_chain):
        """Test processing a streaming generate request."""
        mock_request = GenerateRequest(model=TEST_MODEL, prompt=TEST_PROMPT, stream=TRUE_VALUE)
        mock_response = {"response": "generated text"}
        
        generate_chain.ollama_client.generate = AsyncMock(return_value=mock_response)
        
        result = await generate_chain.process_generate_request(mock_request)
        
        generate_chain.ollama_client.generate.assert_called_once_with(
            model=TEST_MODEL,
            prompt=TEST_PROMPT,
            stream=TRUE_VALUE
        )
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_process_generate_request_error(self, generate_chain):
        """Test processing a generate request that raises an error."""
        mock_request = GenerateRequest(model=TEST_MODEL, prompt=TEST_PROMPT)
        
        generate_chain.ollama_client.generate = AsyncMock(side_effect=Exception("API Error"))
        
        with pytest.raises(Exception, match="API Error"):
            await generate_chain.process_generate_request(mock_request)

    @pytest.mark.asyncio
    async def test_ensure_model_loaded_cache_miss(self, generate_chain):
        """Test ensuring model is loaded when not in cache."""
        generate_chain._model_cache = None
        generate_chain.ollama_client.list = AsyncMock(return_value={"models": [{"name": "existing-model"}]})
        generate_chain.ollama_client.pull = AsyncMock()
        
        await generate_chain._ensure_model_loaded("new-model")
        
        generate_chain.ollama_client.list.assert_called_once()
        generate_chain.ollama_client.pull.assert_called_once_with("new-model")

    @pytest.mark.asyncio
    async def test_ensure_model_loaded_cache_hit(self, generate_chain):
        """Test ensuring model is loaded when already in cache."""
        generate_chain._model_cache = {"existing-model": time.time(), "_timestamp": time.time()}
        generate_chain.ollama_client.list = AsyncMock()
        generate_chain.ollama_client.pull = AsyncMock()
        
        await generate_chain._ensure_model_loaded("existing-model")
        
        generate_chain.ollama_client.list.assert_not_called()
        generate_chain.ollama_client.pull.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_model_loaded_error(self, generate_chain):
        """Test ensuring model is loaded when it raises an error."""
        generate_chain.ollama_client.list = AsyncMock(side_effect=Exception("API Error"))

        with pytest.raises(Exception, match="API Error"):
            await generate_chain._ensure_model_loaded(TEST_MODEL)
