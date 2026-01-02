"""Tests for the optimizer agent functionality."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path

from src.plugins.optimizer.agent import OptimizerAgent, OptimizerMetadata
from src.plugins.optimizer.const import AGENT_NAME, SAFETY_MARGIN
from src.plugins.optimizer.db_utils import Template
from ..test_const import (
    TEST_MODEL, TEST_PROMPT, PROMPT_EVAL_COUNT, EVAL_COUNT,
    INVALID_TOKEN_COUNT, TEMPLATE_ID, CONFIDENCE_SCORE, DISTANCE_VALUE,
    REASONING_TEXT, DEFAULT_CTX_VALUE, NONE_VALUE, EMPTY_STRING,
    WHITESPACE_STRING
)


class TestOptimizerAgent:
    """Test the OptimizerAgent class."""

    @pytest.fixture
    def optimizer_agent(self):
        """Create an OptimizerAgent instance."""
        with patch('src.plugins.optimizer.agent.DatabaseManager'), \
             patch('src.plugins.optimizer.agent.TemplateMatcher'):
            return OptimizerAgent()

    def test_name_property(self, optimizer_agent):
        """Test the name property."""
        assert optimizer_agent.name == AGENT_NAME

    @pytest.mark.asyncio
    async def test_on_request_invalid_request_type(self, optimizer_agent):
        """Test on_request with invalid request type."""
        result = await optimizer_agent.on_request("invalid_request")
        assert result == "invalid_request"

    @pytest.mark.asyncio
    async def test_on_request_no_prompt_text(self, optimizer_agent):
        """Test on_request with no prompt text."""
        context = {"model": TEST_MODEL}
        result = await optimizer_agent.on_request(context)
        assert result == context

    @pytest.mark.asyncio
    async def test_on_request_empty_prompt_text(self, optimizer_agent):
        """Test on_request with empty prompt text."""
        context = {"model": TEST_MODEL, "prompt": EMPTY_STRING}
        result = await optimizer_agent.on_request(context)
        assert result == context

    @pytest.mark.asyncio
    async def test_on_request_whitespace_prompt_text(self, optimizer_agent):
        """Test on_request with whitespace-only prompt text."""
        context = {"model": TEST_MODEL, "prompt": WHITESPACE_STRING}
        result = await optimizer_agent.on_request(context)
        assert result == context

    @pytest.mark.asyncio
    async def test_on_request_with_prompt(self, optimizer_agent):
        """Test on_request with prompt."""
        with patch.object(optimizer_agent, '_extract_prompt_text', return_value=TEST_PROMPT), \
             patch.object(optimizer_agent, '_find_matching_template_async', return_value=None):
            context = {"model": TEST_MODEL, "prompt": TEST_PROMPT}
            result = await optimizer_agent.on_request(context)
            assert result == context

    @pytest.mark.asyncio
    async def test_on_request_with_matching_template(self, optimizer_agent):
        """Test on_request with matching template."""
        mock_match = {
            'template': MagicMock(),
            'resolution': 64,
            'distance': 2,
            'score': 0.9
        }
        mock_match['template'].id = 1
        mock_match['template'].working_window = 1024

        with patch.object(optimizer_agent, '_extract_prompt_text', return_value=TEST_PROMPT), \
             patch.object(optimizer_agent, '_find_matching_template_async', return_value=mock_match), \
             patch.object(optimizer_agent, '_apply_optimizations') as mock_apply:
            context = {"model": TEST_MODEL, "prompt": TEST_PROMPT}
            result = await optimizer_agent.on_request(context)

            assert '_optimizer' in result
            assert isinstance(result['_optimizer'], OptimizerMetadata)

    @pytest.mark.asyncio
    async def test_on_request_exception_handling(self, optimizer_agent):
        """Test on_request exception handling."""
        with patch.object(optimizer_agent, '_extract_prompt_text', side_effect=Exception("Test error")):
            context = {"model": TEST_MODEL, "prompt": TEST_PROMPT}
            result = await optimizer_agent.on_request(context)
            assert result == context

    @pytest.mark.asyncio
    async def test_on_response_invalid_types(self, optimizer_agent):
        """Test on_response with invalid request or response types."""
        result = await optimizer_agent.on_response("invalid", {"response": "test"})
        assert result == {"response": "test"}

        result = await optimizer_agent.on_response({"request": "test"}, "invalid")
        assert result == "invalid"

    @pytest.mark.asyncio
    async def test_on_response_with_token_counts(self, optimizer_agent):
        """Test on_response with token counts."""
        request = {}
        response = {"prompt_eval_count": PROMPT_EVAL_COUNT, "eval_count": EVAL_COUNT}

        with patch.object(optimizer_agent, '_is_valid_token_counts', return_value=True), \
             patch.object(optimizer_agent, '_update_existing_template') as mock_update:
            request['_optimizer'] = OptimizerMetadata(template_id=TEMPLATE_ID, distance=DISTANCE_VALUE)
            result = await optimizer_agent.on_response(request, response)
            
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_response_new_template_learning(self, optimizer_agent):
        """Test on_response learning new template when no optimizer metadata."""
        request = {"prompt": TEST_PROMPT}
        response = {"prompt_eval_count": PROMPT_EVAL_COUNT, "eval_count": EVAL_COUNT}

        with patch.object(optimizer_agent, '_is_valid_token_counts', return_value=True), \
             patch.object(optimizer_agent, '_learn_new_template') as mock_learn:
            result = await optimizer_agent.on_response(request, response)
            
            mock_learn.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_response_invalid_token_counts(self, optimizer_agent):
        """Test on_response with invalid token counts."""
        request = {"prompt": "test prompt"}
        response = {"prompt_eval_count": INVALID_TOKEN_COUNT, "eval_count": INVALID_TOKEN_COUNT}

        with patch.object(optimizer_agent, '_is_valid_token_counts', return_value=False), \
             patch.object(optimizer_agent, '_update_existing_template') as mock_update, \
             patch.object(optimizer_agent, '_learn_new_template') as mock_learn:
            result = await optimizer_agent.on_response(request, response)
            
            mock_update.assert_not_called()
            mock_learn.assert_not_called()

    def test_extract_prompt_text_with_messages(self, optimizer_agent):
        """Test extracting prompt text from messages."""
        context = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"}
            ]
        }
        result = optimizer_agent._extract_prompt_text(context)
        assert "user: Hello" in result
        assert "assistant: Hi there" in result

    def test_extract_prompt_text_with_prompt(self, optimizer_agent):
        """Test extracting prompt text from prompt field."""
        context = {"prompt": "Hello world"}
        result = optimizer_agent._extract_prompt_text(context)
        assert result == "Hello world"

    def test_extract_prompt_text_invalid_messages(self, optimizer_agent):
        """Test extracting prompt text with invalid messages."""
        context = {"messages": "not a list"}
        result = optimizer_agent._extract_prompt_text(context)
        assert result is None

    def test_extract_prompt_text_empty_messages(self, optimizer_agent):
        """Test extracting prompt text with empty messages."""
        context = {"messages": []}
        result = optimizer_agent._extract_prompt_text(context)
        assert result is None

    def test_apply_optimizations_with_working_window(self, optimizer_agent):
        """Test applying optimizations with working window."""
        request = {"options": {}}
        result = optimizer_agent._apply_optimizations(request, 2048)
        assert request['options']['num_ctx'] == 2048

    def test_apply_optimizations_without_working_window(self, optimizer_agent):
        """Test applying optimizations without working window."""
        request = {"options": {}}
        result = optimizer_agent._apply_optimizations(request, None)
        assert 'num_ctx' not in request['options']

    def test_apply_optimizations_initialize_options(self, optimizer_agent):
        """Test applying optimizations when options don't exist."""
        request = {}
        result = optimizer_agent._apply_optimizations(request, DEFAULT_CTX_VALUE)
        assert request['options']['num_ctx'] == DEFAULT_CTX_VALUE

    def test_is_valid_token_counts_valid(self, optimizer_agent):
        """Test valid token counts."""
        result = optimizer_agent._is_valid_token_counts(PROMPT_EVAL_COUNT, EVAL_COUNT)
        assert result is True

    def test_is_valid_token_counts_invalid(self, optimizer_agent):
        """Test invalid token counts."""
        result = optimizer_agent._is_valid_token_counts(INVALID_TOKEN_COUNT, EVAL_COUNT)
        assert result is False

        result = optimizer_agent._is_valid_token_counts(PROMPT_EVAL_COUNT, INVALID_TOKEN_COUNT)
        assert result is False

        result = optimizer_agent._is_valid_token_counts("invalid", 50)
        assert result is False

        result = optimizer_agent._is_valid_token_counts(100, "invalid")
        assert result is False


class TestOptimizerMetadata:
    """Test the OptimizerMetadata class."""

    def test_optimizer_metadata_creation(self):
        """Test creating OptimizerMetadata instance."""
        metadata = OptimizerMetadata(
            template_id=TEMPLATE_ID,
            confidence=CONFIDENCE_SCORE,
            distance=DISTANCE_VALUE,
            reasoning=REASONING_TEXT
        )
        
        assert metadata.template_id == TEMPLATE_ID
        assert metadata.confidence == CONFIDENCE_SCORE
        assert metadata.distance == DISTANCE_VALUE
        assert metadata.reasoning == REASONING_TEXT

    def test_optimizer_metadata_defaults(self):
        """Test OptimizerMetadata with default values."""
        metadata = OptimizerMetadata()
        
        assert metadata.template_id is NONE_VALUE
        assert metadata.confidence is NONE_VALUE
        assert metadata.distance is NONE_VALUE
        assert metadata.distance is NONE_VALUE
        assert metadata.reasoning is NONE_VALUE
