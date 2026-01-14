"""Tests for agent streaming functionality during streaming."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.shared.base_agent import BaseAgent
from src.slices.base_chain import BaseChain
from src.plugins.example_agent.agent import ExampleAgent
from src.plugins.optimizer.agent import OptimizerAgent
from src.plugins.rag.agent import RagAgent


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
def example_agent():
    """Create an example agent instance."""
    return ExampleAgent()


@pytest.fixture
def optimizer_agent():
    """Create an optimizer agent instance."""
    # Mock the repository for testing
    mock_repo = MagicMock()
    mock_repo.update_template = MagicMock()
    mock_repo.close = MagicMock()
    
    agent = OptimizerAgent(repository=mock_repo)
    return agent


@pytest.fixture
def rag_agent():
    """Create a RAG agent instance."""
    return RagAgent()


@pytest.fixture
def mock_chain():
    """Create a mock chain for testing."""
    registry = MockRegistry()
    return MockBaseChain(registry)


def test_base_agent_has_no_on_response_stream_method():
    """Test that BaseAgent no longer has the on_response_stream method."""
    # The base agent should not have the method anymore
    class TestAgent(BaseAgent):
        def __init__(self):
            self._name = "test"

        @property
        def name(self) -> str:
            return self._name

        async def on_request(self, request: dict) -> dict:
            return request

        async def on_response(self, request: dict, response: dict) -> dict:
            return response
    
    # Should not have the on_response_stream method
    agent = TestAgent()
    assert not hasattr(agent, 'on_response_stream')