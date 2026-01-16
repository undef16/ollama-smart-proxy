"""Tests for the MoA agent functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from src.plugins.moa.agent import MoAAgent


class TestMoAAgent:
    """Test the MoAAgent class."""

    @pytest.fixture
    def moa_agent(self):
        """Create a MoAAgent instance."""
        with patch('src.shared.config.Config') as mock_config, \
             patch('src.shared.logging.LoggingManager.get_logger') as mock_logger, \
             patch('src.plugins.moa.moa_config.MoAConfigModel.from_env_and_json') as mock_moa_config:
            mock_config.return_value.ollama_host = "localhost"
            mock_config.return_value.ollama_port = 11434

            # Create a mock MoA config
            mock_config_obj = MagicMock()
            mock_config_obj.moa_models = ["gemma3:1b", "gemma3:1b", "gemma3:1b"]
            mock_config_obj.timeout = 300
            mock_config_obj.max_models = 3
            mock_config_obj.prompts = {
                "ranking_prompt": "You are evaluating the model's response...",
                "batch_ranking_prompt": "You are evaluating multiple model responses..."
            }
            mock_moa_config.return_value = mock_config_obj

            mock_logger.return_value = MagicMock()
            agent = MoAAgent()
            agent.http_client = AsyncMock()  # Mock the HTTP client
            return agent

    def test_name_property(self, moa_agent):
        """Test the name property."""
        assert moa_agent.name == "moa"

    def test_extract_query_no_messages(self, moa_agent):
        """Test extract_query with no messages."""
        request = {}
        assert moa_agent.extract_query(request) == ""

    def test_extract_query_without_moa(self, moa_agent):
        """Test extract_query with message not starting with /moa."""
        request = {"messages": [{"role": "user", "content": "Hello world"}], "prompt": ""}
        assert moa_agent.extract_query(request) == "Hello world"

    def test_extract_query_with_moa(self, moa_agent):
        """Test extract_query with message starting with /moa."""
        request = {"messages": [{"role": "user", "content": "/moa What is AI?"}], "prompt": ""}
        assert moa_agent.extract_query(request) == "What is AI?"

    def test_extract_query_moa_only(self, moa_agent):
        """Test extract_query with /moa only."""
        request = {"messages": [{"role": "user", "content": "/moa"}], "prompt": ""}
        assert moa_agent.extract_query(request) == ""

    def test_extract_query_from_prompt(self, moa_agent):
        """Test extract_query from prompt field."""
        request = {"prompt": "/moa What is AI?"}
        assert moa_agent.extract_query(request) == "What is AI?"

    @pytest.mark.asyncio
    async def test_on_request_not_activated(self, moa_agent):
        """Test on_request when MoA is not activated."""
        request = {"messages": [{"role": "user", "content": "Hello world"}]}
        result = await moa_agent.on_request(request)
        assert result == request

    @pytest.mark.asyncio
    async def test_on_request_no_query(self, moa_agent):
        """Test on_request with /moa but no query."""
        request = {"messages": [{"role": "user", "content": "/moa"}]}
        result = await moa_agent.on_request(request)
        assert result == request  # Should return original request

    @pytest.mark.asyncio
    async def test_collect_responses_success(self, moa_agent):
        """Test collect_responses with successful model queries."""
        query = "What is AI?"
        models = ["llama3.2", "mistral"]

        # Mock the _query_ollama method
        moa_agent._query_ollama = AsyncMock(side_effect=[
            "AI is artificial intelligence.",
            "AI stands for Artificial Intelligence."
        ])

        responses = await moa_agent.collect_responses(query, models)

        assert len(responses) == 2
        assert responses[0]["model"] == "llama3.2"
        assert responses[0]["response"] == "AI is artificial intelligence."
        assert responses[1]["model"] == "mistral"
        assert responses[1]["response"] == "AI stands for Artificial Intelligence."

    @pytest.mark.asyncio
    async def test_collect_responses_partial_failure(self, moa_agent):
        """Test collect_responses with some model failures."""
        query = "What is AI?"
        models = ["llama3.2", "mistral", "gemma2"]

        # Mock the _query_ollama method - one failure
        moa_agent._query_ollama = AsyncMock(side_effect=[
            "AI is artificial intelligence.",
            None,  # Failure
            "AI stands for Artificial Intelligence."
        ])

        responses = await moa_agent.collect_responses(query, models)

        assert len(responses) == 2
        assert responses[0]["model"] == "llama3.2"
        assert responses[1]["model"] == "gemma2"

    @pytest.mark.asyncio
    async def test_collect_responses_all_failures(self, moa_agent):
        """Test collect_responses with all models failing."""
        query = "What is AI?"
        models = ["llama3.2", "mistral"]

        # Mock the _query_ollama method - all failures
        moa_agent._query_ollama = AsyncMock(return_value=None)

        responses = await moa_agent.collect_responses(query, models)

        assert len(responses) == 0

    @pytest.mark.asyncio
    async def test_on_request_success_flow(self, moa_agent):
        """Test the complete on_request flow with successful responses."""
        query = "What is AI?"
        request = {"messages": [{"role": "user", "content": f"/moa {query}"}]}

        # Mock responses for the entire workflow
        moa_agent.collect_responses = AsyncMock(return_value=[
            {"model": "model1", "response": "Response 1"},
            {"model": "model2", "response": "Response 2"}
        ])

        moa_agent.collect_rankings = AsyncMock(return_value="Final synthesized response")

        result = await moa_agent.on_request(request)

        # Verify the response structure
        assert "message" in result
        assert result["message"]["role"] == "assistant"
        assert result["message"]["content"] == "Final synthesized response"
        assert result["done"] == True

        # Verify the workflow methods were called
        moa_agent.collect_responses.assert_called_once_with(query, moa_agent.moa_models[:moa_agent.max_models])
        moa_agent.collect_rankings.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_request_stage1_failure(self, moa_agent):
        """Test on_request when stage 1 (collect responses) fails."""
        query = "What is AI?"
        request = {"messages": [{"role": "user", "content": f"/moa {query}"}]}

        # Mock stage 1 to return empty responses
        moa_agent.collect_responses = AsyncMock(return_value=[])

        result = await moa_agent.on_request(request)

        # Should return an error response
        assert "message" in result
        assert "MoA failed: No responses collected" in result["message"]["content"]

    @pytest.mark.asyncio
    async def test_on_request_exception_handling(self, moa_agent):
        """Test on_request exception handling."""
        query = "What is AI?"
        request = {"messages": [{"role": "user", "content": f"/moa {query}"}]}

        # Make collect_responses raise an exception
        moa_agent.collect_responses = AsyncMock(side_effect=Exception("Test error"))

        result = await moa_agent.on_request(request)

        # Should return an error response
        assert "message" in result
        assert "MoA process failed: Test error" in result["message"]["content"]

    @pytest.mark.asyncio
    async def test_query_ollama_success(self, moa_agent):
        """Test _query_ollama with successful response."""
        moa_agent.http_client.post = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "Test response"}
        }
        mock_response.raise_for_status.return_value = None
        moa_agent.http_client.post.return_value = mock_response

        result = await moa_agent._query_ollama("test-model", "test prompt")

        assert result == "Test response"
        moa_agent.http_client.post.assert_called_once()
        args, kwargs = moa_agent.http_client.post.call_args
        payload = kwargs['json']
        assert payload['model'] == 'test-model'
        assert payload['messages'][0]['content'] == 'test prompt'

    @pytest.mark.asyncio
    async def test_query_ollama_failure(self, moa_agent):
        """Test _query_ollama with failure."""
        moa_agent.http_client.post = AsyncMock()
        moa_agent.http_client.post.side_effect = Exception("Network error")

        result = await moa_agent._query_ollama("test-model", "test prompt")

        assert result is None

    def test_create_moa_response_chat_format(self, moa_agent):
        """Test _create_moa_response for chat format."""
        request = {"messages": [{"role": "user", "content": "test"}]}
        result = moa_agent._create_moa_response("test content", request)

        assert result["message"]["role"] == "assistant"
        assert result["message"]["content"] == "test content"
        assert result["done"] == True

    def test_create_moa_response_generate_format(self, moa_agent):
        """Test _create_moa_response for generate format."""
        request = {"prompt": "test"}
        result = moa_agent._create_moa_response("test content", request)

        assert result["response"] == "test content"
        assert result["done"] == True

    def test_create_error_response(self, moa_agent):
        """Test _create_error_response method."""
        request = {"messages": [{"role": "user", "content": "test"}]}
        result = moa_agent._create_error_response("error message", request)

        assert result["message"]["role"] == "assistant"
        assert result["message"]["content"] == "error message"
        assert result["done"] == True