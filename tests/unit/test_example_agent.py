"""Tests for the example agent functionality."""

import pytest
from unittest.mock import AsyncMock

from src.plugins.example_agent.agent import ExampleAgent


class TestExampleAgent:
    """Test the ExampleAgent class."""

    @pytest.fixture
    def example_agent(self):
        """Create an ExampleAgent instance."""
        return ExampleAgent()

    def test_name_property(self, example_agent):
        """Test the name property."""
        assert example_agent.name == "example"

    @pytest.mark.asyncio
    async def test_on_request_no_messages(self, example_agent):
        """Test on_request with no messages."""
        context = {"model": "test-model", "prompt": "test prompt"}

        result = await example_agent.on_request(context)

        assert result == context

    @pytest.mark.asyncio
    async def test_on_request_with_non_user_message(self, example_agent):
        """Test on_request with a non-user message."""
        context = {
            "messages": [
                {"role": "assistant", "content": "Hello from assistant"}
            ]
        }

        result = await example_agent.on_request(context)

        assert result == context
        assert result["messages"][0]["content"] == "Hello from assistant"

    @pytest.mark.asyncio
    async def test_on_request_with_user_message(self, example_agent):
        """Test on_request with a user message."""
        context = {
            "messages": [
                {"role": "user", "content": "Hello from user"}
            ]
        }

        result = await example_agent.on_request(context)

        assert result["messages"][0]["content"] == "[Example Agent] Hello from user"

    @pytest.mark.asyncio
    async def test_on_request_multiple_messages(self, example_agent):
        """Test on_request with multiple messages."""
        context = {
            "messages": [
                {"role": "assistant", "content": "Hello from assistant"},
                {"role": "system", "content": "System message"},
                {"role": "user", "content": "Hello from user"}
            ]
        }

        result = await example_agent.on_request(context)

        assert result["messages"][0]["content"] == "Hello from assistant"
        assert result["messages"][1]["content"] == "System message"
        assert result["messages"][2]["content"] == "[Example Agent] Hello from user"

    @pytest.mark.asyncio
    async def test_on_response_chat_format(self, example_agent):
        """Test on_response with chat format (message.content)."""
        context = {
            "message": {
                "content": "Hello from model"
            }
        }

        result = await example_agent.on_response(context)

        assert result["message"]["content"] == "Hello from model [processed by example agent]"

    @pytest.mark.asyncio
    async def test_on_response_generate_format(self, example_agent):
        """Test on_response with generate format (response)."""
        context = {
            "response": "Generated text from model"
        }

        result = await example_agent.on_response(context)

        assert result["response"] == "Generated text from model [processed by example agent]"

    @pytest.mark.asyncio
    async def test_on_response_no_matching_format(self, example_agent):
        """Test on_response with no matching format."""
        context = {
            "other_field": "some value"
        }

        result = await example_agent.on_response(context)

        assert result == context