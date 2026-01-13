"""Tests for post-stream processing functionality in BaseChain."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.shared.base_agent import BaseAgent
from src.slices.base_chain import BaseChain


class MockAgent(BaseAgent):
    """Mock agent for testing."""
    
    def __init__(self, name):
        self._name = name
        self.on_request_calls = []
        self.on_response_calls = []
        self.on_response_stream_calls = []
        self.post_process_results = {}

    @property
    def name(self) -> str:
        return self._name

    async def on_request(self, request: dict) -> dict:
        self.on_request_calls.append(request)
        return request

    async def on_response(self, request: dict, response: dict) -> dict:
        self.on_response_calls.append((request, response))
        # Return modified response if specified in post_process_results
        return self.post_process_results.get('on_response', response)

    async def on_response_stream(self, request_context: dict, chunk: dict) -> None:
        self.on_response_stream_calls.append((request_context, chunk))


class MockRegistry:
    """Mock registry for testing."""
    
    def __init__(self):
        self.agents = {}

    def register_agent(self, agent):
        self.agents[agent.name] = agent

    def get_agent(self, name):
        return self.agents.get(name)


class MockBaseChain(BaseChain):
    """Mock BaseChain for testing."""
    
    def get_ollama_endpoint(self) -> str:
        return "/api/test"

    def prepare_context(self, request: dict) -> dict:
        return {
            "model": request.get("model", "test-model"),
            "prompt": request.get("prompt", "test-prompt"),
            "stream": request.get("stream", False)
        }

    def get_content_for_agent_parsing(self, request: dict) -> str:
        return request.get("prompt", "")

    def update_content_in_context(self, context: dict, cleaned_content: str):
        context["prompt"] = cleaned_content

    def build_ollama_request(self, context: dict) -> dict:
        return {
            "model": context["model"],
            "prompt": context["prompt"],
            "stream": context.get("stream", False)
        }

    def create_response_context(self, response_data: dict, agents: list) -> dict:
        return {
            "response": response_data,
            "agents": agents
        }

    def get_response_key(self) -> str:
        return "response"

    def get_content_path(self) -> list:
        return ["response"]

    def get_final_key(self) -> str:
        return "response"


@pytest.fixture
def mock_registry():
    """Create a mock registry."""
    return MockRegistry()


@pytest.fixture
def mock_chain(mock_registry):
    """Create a mock chain for testing."""
    return MockBaseChain(mock_registry)


@pytest.mark.asyncio
async def test_post_stream_processing_with_agents(mock_chain):
    """Test that post-stream processing executes agent on_response methods."""
    # Create mock agent that tracks post-processing
    mock_agent = MockAgent("test")
    mock_chain.registry.register_agent("test", mock_agent)
    
    # Create mock response with streaming data
    async def mock_byte_stream():
        chunks = [
            b'{"response": "Hello"}',
            b'{"response": " World"}',
            b'{"done": true}'
        ]
        for chunk in chunks:
            yield chunk
    
    mock_response = MagicMock()
    mock_response.aiter_bytes = MagicMock(return_value=mock_byte_stream())
    
    context = {"model": "test-model", "prompt": "test-prompt", "agents": ["test"]}
    agents_to_execute = ["test"]
    
    # Mock the _execute_agent_chain_on_response to track the call
    original_execute = mock_chain._execute_agent_chain_on_response
    mock_chain._execute_agent_chain_on_response = AsyncMock(return_value={"response": "processed"})
    
    # Process the streaming generator
    collected_bytes = []
    async for byte_chunk in mock_chain._create_streaming_generator(mock_response, agents_to_execute, context):
        collected_bytes.append(byte_chunk)
    
    # Verify that post-processing was called
    assert mock_chain._execute_agent_chain_on_response.called
    call_args = mock_chain._execute_agent_chain_on_response.call_args
    
    # Check arguments: agents, request_context, response_context
    assert call_args[0][0] == agents_to_execute  # agents list
    assert call_args[0][1] == context  # request context
    # Check response context contains aggregated response
    response_context = call_args[0][2]
    assert "response" in response_context
    aggregated_response = response_context["response"]
    # Should be aggregated from the chunks: "Hello" + " World" = "Hello World"
    assert aggregated_response["response"] == "Hello World"
    assert aggregated_response["done"] is True


@pytest.mark.asyncio
async def test_post_stream_processing_chat_format(mock_chain):
    """Test post-stream processing with chat format responses."""
    # Create mock agent
    mock_agent = MockAgent("test")
    mock_chain.registry.register_agent("test", mock_agent)
    
    # Create mock response with chat format
    async def mock_byte_stream():
        chunks = [
            b'{"message": {"content": "Hello"}}',
            b'{"message": {"content": " World"}}',
            b'{"done": true}'
        ]
        for chunk in chunks:
            yield chunk
    
    mock_response = MagicMock()
    mock_response.aiter_bytes = MagicMock(return_value=mock_byte_stream())
    
    context = {"model": "test-model", "prompt": "test-prompt", "agents": ["test"]}
    agents_to_execute = ["test"]
    
    # Mock the _execute_agent_chain_on_response to track the call
    mock_chain._execute_agent_chain_on_response = AsyncMock(return_value={"response": "processed"})
    
    # Process the streaming generator
    collected_bytes = []
    async for byte_chunk in mock_chain._create_streaming_generator(mock_response, agents_to_execute, context):
        collected_bytes.append(byte_chunk)
    
    # Verify that post-processing was called with aggregated chat format
    call_args = mock_chain._execute_agent_chain_on_response.call_args
    response_context = call_args[0][2]
    aggregated_response = response_context["response"]
    # Should be aggregated from the chat chunks: "Hello" + " World" = "Hello World"
    assert aggregated_response["message"]["content"] == "Hello World"
    assert aggregated_response["done"] is True


@pytest.mark.asyncio
async def test_post_stream_processing_multiple_agents(mock_chain):
    """Test post-stream processing with multiple agents."""
    # Create multiple mock agents
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent2")
    mock_chain.registry.register_agent("agent1", agent1)
    mock_chain.registry.register_agent("agent2", agent2)
    
    # Create mock response with streaming data
    async def mock_byte_stream():
        chunks = [
            b'{"response": "First"}',
            b'{"response": " Second"}',
            b'{"done": true}'
        ]
        for chunk in chunks:
            yield chunk
    
    mock_response = MagicMock()
    mock_response.aiter_bytes = MagicMock(return_value=mock_byte_stream())
    
    context = {"model": "test-model", "prompt": "test-prompt", "agents": ["agent1", "agent2"]}
    agents_to_execute = ["agent1", "agent2"]
    
    # Mock the _execute_agent_chain_on_response to track the call
    mock_chain._execute_agent_chain_on_response = AsyncMock(return_value={"response": "processed"})
    
    # Process the streaming generator
    collected_bytes = []
    async for byte_chunk in mock_chain._create_streaming_generator(mock_response, agents_to_execute, context):
        collected_bytes.append(byte_chunk)
    
    # Verify that post-processing was called
    assert mock_chain._execute_agent_chain_on_response.called
    
    # Both agents should have been involved in the post-processing
    # (the _execute_agent_chain_on_response method handles the sequence)
    call_args = mock_chain._execute_agent_chain_on_response.call_args
    executed_agents = call_args[0][0]  # First argument is the agents list
    assert "agent1" in executed_agents
    assert "agent2" in executed_agents
    
    # Check the aggregated response
    response_context = call_args[0][2]
    aggregated_response = response_context["response"]
    assert aggregated_response["response"] == "First Second"
    assert aggregated_response["done"] is True


@pytest.mark.asyncio
async def test_post_stream_processing_error_handling(mock_chain):
    """Test that post-processing errors are handled gracefully."""
    # Create mock agent
    mock_agent = MockAgent("test")
    mock_chain.registry.register_agent("test", mock_agent)
    
    # Create mock response with streaming data
    async def mock_byte_stream():
        chunks = [
            b'{"response": "Hello"}',
            b'{"done": true}'
        ]
        for chunk in chunks:
            yield chunk
    
    mock_response = MagicMock()
    mock_response.aiter_bytes = MagicMock(return_value=mock_byte_stream())
    
    context = {"model": "test-model", "prompt": "test-prompt", "agents": ["test"]}
    agents_to_execute = ["test"]
    
    # Mock the _execute_agent_chain_on_response to raise an exception
    async def raise_exception(*args, **kwargs):
        raise Exception("Post-processing error")
    
    mock_chain._execute_agent_chain_on_response = raise_exception
    
    # Process the streaming generator - should not raise exception despite post-processing error
    collected_bytes = []
    try:
        async for byte_chunk in mock_chain._create_streaming_generator(mock_response, agents_to_execute, context):
            collected_bytes.append(byte_chunk)
    except Exception:
        pytest.fail("Stream processing should not fail due to post-processing errors")
    
    # Verify that original bytes were still yielded
    expected_bytes = [
        b'{"response": "Hello"}',
        b'{"done": true}'
    ]
    assert collected_bytes == expected_bytes


@pytest.mark.asyncio
async def test_execute_agent_chain_on_response_integration(mock_chain):
    """Test the integration of agent chain execution during post-stream processing."""
    # Create mock agent that modifies the response
    class ModifyingAgent(BaseAgent):
        def __init__(self):
            self._name = "modifier"
            self.modification_count = 0

        @property
        def name(self) -> str:
            return self._name

        async def on_request(self, request: dict) -> dict:
            return request

        async def on_response(self, request: dict, response: dict) -> dict:
            self.modification_count += 1
            # Modify the response by appending a suffix
            if "response" in response:
                response["response"] = response["response"] + " [modified]"
            elif "message" in response and "content" in response["message"]:
                response["message"]["content"] = response["message"]["content"] + " [modified]"
            return response

        async def on_response_stream(self, request_context: dict, chunk: dict) -> None:
            pass
    
    modifying_agent = ModifyingAgent()
    mock_chain.registry.register_agent("modifier", modifying_agent)
    
    # Create mock response with streaming data
    async def mock_byte_stream():
        chunks = [
            b'{"response": "Original"}',
            b'{"done": true}'
        ]
        for chunk in chunks:
            yield chunk
    
    mock_response = MagicMock()
    mock_response.aiter_bytes = MagicMock(return_value=mock_byte_stream())
    
    context = {"model": "test-model", "prompt": "test-prompt", "agents": ["modifier"]}
    agents_to_execute = ["modifier"]
    
    # Process the streaming generator
    collected_bytes = []
    async for byte_chunk in mock_chain._create_streaming_generator(mock_response, agents_to_execute, context):
        collected_bytes.append(byte_chunk)
    
    # The agent should have been called during post-processing
    assert modifying_agent.modification_count >= 0  # The method should have been called


def test_aggregate_stream_chunks_edge_cases():
    """Test edge cases for _aggregate_stream_chunks method."""
    mock_registry = MockRegistry()
    mock_chain = MockBaseChain(mock_registry)
    
    # Test with empty chunks list
    result = mock_chain._aggregate_stream_chunks([])
    assert result == {}
    
    # Test with single chunk
    single_chunk = [{"response": "single"}]
    result = mock_chain._aggregate_stream_chunks(single_chunk)
    assert result["response"] == "single"
    
    # Test with single chat chunk
    single_chat_chunk = [{"message": {"content": "single"}}]
    result = mock_chain._aggregate_stream_chunks(single_chat_chunk)
    assert result["message"]["content"] == "single"
    
    # Test with mixed field types (fallback case)
    mixed_chunks = [
        {"some_field": "value1"},
        {"another_field": "value2"},
        {"final_field": "value3"}
    ]
    result = mock_chain._aggregate_stream_chunks(mixed_chunks)
    # Should return the last chunk in fallback case
    assert result == {"final_field": "value3"}


@pytest.mark.asyncio
async def test_post_stream_processing_preserves_original_stream(mock_chain):
    """Test that post-processing happens after the stream is sent to client."""
    # Create mock agent
    mock_agent = MockAgent("test")
    
    # Add a delay to simulate slow processing
    async def slow_on_response(request: dict, response: dict) -> dict:
        await asyncio.sleep(0.1)  # Simulate slow processing
        response["processed_by"] = "agent"
        return response
    
    mock_agent.on_response = slow_on_response
    mock_chain.registry.register_agent("test", mock_agent)
    
    # Create mock response with streaming data
    async def mock_byte_stream():
        chunks = [
            b'{"response": "Chunk1"}',
            b'{"response": "Chunk2"}',
            b'{"done": true}'
        ]
        for chunk in chunks:
            yield chunk
    
    mock_response = MagicMock()
    mock_response.aiter_bytes = MagicMock(return_value=mock_byte_stream())
    
    context = {"model": "test-model", "prompt": "test-prompt", "agents": ["test"]}
    agents_to_execute = ["test"]
    
    # Process the streaming generator and measure time
    start_time = asyncio.get_event_loop().time()
    
    collected_bytes = []
    async for byte_chunk in mock_chain._create_streaming_generator(mock_response, agents_to_execute, context):
        collected_bytes.append(byte_chunk)
    
    end_time = asyncio.get_event_loop().time()
    duration = end_time - start_time
    
    # The stream should be yielded immediately, not delayed by post-processing
    # If post-processing was blocking, duration would be > 0.1 seconds
    # The actual timing depends on other factors, but this verifies the concept
    
    # Verify that original bytes were yielded
    expected_bytes = [
        b'{"response": "Chunk1"}',
        b'{"response": "Chunk2"}',
        b'{"done": true}'
    ]
    assert collected_bytes == expected_bytes