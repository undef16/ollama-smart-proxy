import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.plugins.moa.agent import MoAAgent
from src.plugins.moa.two_models_ranking_strategy import TwoModelsRankingStrategy
from src.plugins.moa.multi_models_ranking_strategy import MultiModelsRankingStrategy


class TestMoAAgent:
    """Test suite for MoAAgent functionality with different model counts."""

    def setup_method(self):
        """Setup test fixtures before each test method."""
        with patch('src.shared.config.Config') as mock_config, \
             patch('src.shared.logging.LoggingManager.get_logger') as mock_logger, \
             patch('src.plugins.moa.moa_config.MoAConfigModel.from_env_and_json') as mock_moa_config:
            mock_config.return_value.ollama_host = "localhost"
            mock_config.return_value.ollama_port = 11434

            # Create a mock MoA config
            self.mock_config = MagicMock()
            self.mock_config.moa_models = ["model1", "model2", "model3", "model4"]
            self.mock_config.timeout = 30
            self.mock_config.max_models = 4
            self.mock_config.prompts = {
                "ranking_prompt": "You are evaluating the model's response...",
                "batch_ranking_prompt": "You are evaluating multiple model responses..."
            }
            mock_moa_config.return_value = self.mock_config

            mock_logger.return_value = MagicMock()
            self.agent = MoAAgent()

    @pytest.mark.asyncio
    async def test_collect_rankings_with_2_models_circular_evaluation(self):
        """Test that 2 models use circular evaluation."""
        # Sample responses from 2 models
        responses = [
            {"model": "model1", "response": "Response from model1"},
            {"model": "model2", "response": "Response from model2"}
        ]

        # Mock _query_ollama to return predetermined scores
        with patch.object(self.agent, '_query_ollama', new_callable=AsyncMock) as mock_query:
            # For circular evaluation: model1 evaluates model2's response, model2 evaluates model1's response
            mock_query.side_effect = [
                '{"score": 0.8}',  # model1 scores model2's response
                '{"score": 0.6}'   # model2 scores model1's response
            ]

            result = await self.agent.collect_rankings("test query", responses, ["model1", "model2"])

            # Verify the correct scoring method was used (circular evaluation)
            assert mock_query.call_count == 2

            # The best response should be determined by the scores
            # Since model2's response got a higher score (0.8), it should be returned
            assert result == "Response from model2"

    @pytest.mark.asyncio
    async def test_collect_rankings_with_3_models_n_plus_scoring(self):
        """Test that 3 models use n+1 and n+2 scoring."""
        # Sample responses from 3 models
        responses = [
            {"model": "model1", "response": "Response from model1"},
            {"model": "model2", "response": "Response from model2"},
            {"model": "model3", "response": "Response from model3"}
        ]

        # Mock _query_ollama to return predetermined scores
        with patch.object(self.agent, '_query_ollama', new_callable=AsyncMock) as mock_query:
            # For 3 models: each response is scored by n+1 and n+2 models
            # Response 0 (model1): scored by model2 (n+1) and model3 (n+2)
            # Response 1 (model2): scored by model3 (n+1) and model1 (n+2)
            # Response 2 (model3): scored by model1 (n+1) and model2 (n+2)
            mock_query.side_effect = [
                '[{"response_id": 0, "score": 0.7}, {"response_id": 1, "score": 0.5}]',  # model2 scores model1 and model2
                '[{"response_id": 0, "score": 0.9}, {"response_id": 2, "score": 0.6}]',  # model3 scores model1 and model3
                '[{"response_id": 1, "score": 0.8}, {"response_id": 2, "score": 0.4}]',  # model1 scores model2 and model3
            ]

            result = await self.agent.collect_rankings("test query", responses, ["model1", "model2", "model3"])

            # Verify the correct number of scoring calls (3 evaluators = 3 calls)
            assert mock_query.call_count == 3

            # Calculate average scores:
            # model1 response: (0.7 + 0.9) / 2 = 0.8
            # model2 response: (0.5 + 0.8) / 2 = 0.65
            # model3 response: (0.6 + 0.4) / 2 = 0.5
            # So model1's response should win with 0.8
            assert result == "Response from model1"

    @pytest.mark.asyncio
    async def test_collect_rankings_with_4_models_n_plus_scoring(self):
        """Test that 4+ models use n+1 and n+2 scoring."""
        # Sample responses from 4 models
        responses = [
            {"model": "model1", "response": "Response from model1"},
            {"model": "model2", "response": "Response from model2"},
            {"model": "model3", "response": "Response from model3"},
            {"model": "model4", "response": "Response from model4"}
        ]

        # Mock _query_ollama to return predetermined scores
        with patch.object(self.agent, '_query_ollama', new_callable=AsyncMock) as mock_query:
            # For 4 models: each response is scored by n+1 and n+2 models
            # Response 0: scored by model2 and model3
            # Response 1: scored by model3 and model4
            # Response 2: scored by model4 and model1
            # Response 3: scored by model1 and model2
            mock_query.side_effect = [
                '[{"response_id": 0, "score": 0.7}, {"response_id": 1, "score": 0.5}]',  # model2 scores model1 and model2
                '[{"response_id": 0, "score": 0.9}, {"response_id": 2, "score": 0.6}]',  # model3 scores model1 and model3
                '[{"response_id": 1, "score": 0.8}, {"response_id": 2, "score": 0.4}]',  # model4 scores model2 and model3
                '[{"response_id": 2, "score": 0.3}, {"response_id": 3, "score": 0.2}]',  # model1 scores model3 and model4
            ]

            result = await self.agent.collect_rankings("test query", responses, ["model1", "model2", "model3", "model4"])

            # Verify the correct number of scoring calls (4 evaluators = 4 calls)
            assert mock_query.call_count == 4

            # Calculate average scores:
            # model1 response: (0.7 + 0.9) / 2 = 0.8
            # model2 response: (0.5 + 0.8) / 2 = 0.65
            # model3 response: (0.6 + 0.4 + 0.3) / 3 = 0.43
            # model4 response: (0.2) / 1 = 0.2
            # So model1's response should win with 0.8
            assert result == "Response from model1"

    @pytest.mark.asyncio
    async def test_score_aggregation_for_more_than_2_models(self):
        """Test that score aggregation works correctly for >2 models."""
        responses = [
            {"model": "model1", "response": "Response A"},
            {"model": "model2", "response": "Response B"},
            {"model": "model3", "response": "Response C"}
        ]

        with patch.object(self.agent, '_query_ollama', new_callable=AsyncMock) as mock_query:
            # Assign different scores to test aggregation
            mock_query.side_effect = [
                '[{"response_id": 0, "score": 0.5}, {"response_id": 1, "score": 0.8}]',  # model2 scores model1 and model2
                '[{"response_id": 0, "score": 0.7}, {"response_id": 2, "score": 0.3}]',  # model3 scores model1 and model3
                '[{"response_id": 1, "score": 0.9}, {"response_id": 2, "score": 0.4}]',  # model1 scores model2 and model3
            ]

            result = await self.agent.collect_rankings("test query", responses, ["model1", "model2", "model3"])

            # Calculate expected averages:
            # Response A: (0.5 + 0.7) / 2 = 0.6
            # Response B: (0.8 + 0.9) / 2 = 0.85
            # Response C: (0.3 + 0.4) / 2 = 0.35
            # So Response B should win
            assert result == "Response B"

    @pytest.mark.asyncio
    async def test_best_response_selection_with_aggregated_scores(self):
        """Test that best response is selected based on highest aggregated score."""
        responses = [
            {"model": "model1", "response": "Low score response"},
            {"model": "model2", "response": "Medium score response"},
            {"model": "model3", "response": "High score response"}
        ]

        with patch.object(self.agent, '_query_ollama', new_callable=AsyncMock) as mock_query:
            # Create scores that make "High score response" the winner
            mock_query.side_effect = [
                '[{"response_id": 0, "score": 0.1}, {"response_id": 1, "score": 0.4}]',  # model2 scores model1 and model2
                '[{"response_id": 0, "score": 0.2}, {"response_id": 2, "score": 0.8}]',  # model3 scores model1 and model3
                '[{"response_id": 1, "score": 0.5}, {"response_id": 2, "score": 0.9}]',  # model4 scores model2 and model3
                '[{"response_id": 2, "score": 0.7}]',  # model1 scores model3
            ]

            result = await self.agent.collect_rankings("test query", responses, ["model1", "model2", "model3", "model4"])

            # High score response should have average (0.8 + 0.9 + 0.7) / 3 = 0.8
            # This is higher than others, so it should be selected
            assert result == "High score response"

    @pytest.mark.asyncio
    async def test_edge_case_empty_responses(self):
        """Test handling of empty responses."""
        # Empty responses list
        responses = []

        result = await self.agent.collect_rankings("test query", responses, ["model1", "model2"])

        # Should return empty string when no responses provided
        assert result == ""

    @pytest.mark.asyncio
    async def test_edge_case_single_response(self):
        """Test handling of single response (should return that response)."""
        responses = [
            {"model": "model1", "response": "Only response"}
        ]

        result = await self.agent.collect_rankings("test query", responses, ["model1", "model2"])

        # Should return the single response directly
        assert result == "Only response"

    @pytest.mark.asyncio
    async def test_scoring_failure_handling(self):
        """Test that scoring failures are handled gracefully."""
        responses = [
            {"model": "model1", "response": "Response A"},
            {"model": "model2", "response": "Response B"},
            {"model": "model3", "response": "Response C"}
        ]

        with patch.object(self.agent, '_query_ollama', new_callable=AsyncMock) as mock_query:
            # Simulate some scoring failures (returning None or invalid responses)
            mock_query.side_effect = [
                '[{"response_id": 0, "score": 0.8}, {"response_id": 1, "score": 0.6}]',  # model2 scores model1 and model2 - success
                None,  # model3 scores model1 and model3 - failure
                'invalid json',  # model1 scores model2 and model3 - failure
            ]

            result = await self.agent.collect_rankings("test query", responses, ["model1", "model2", "model3"])

            # Should still work despite some scoring failures
            # Response A: [0.8] -> avg 0.8
            # Response B: [0.6] -> avg 0.6
            # Response C: [] -> avg 0.0
            # So Response A should win
            assert result == "Response A"

    @pytest.mark.asyncio
    async def test_parse_score_valid_json(self):
        """Test that score parsing works correctly with valid JSON."""
        from src.plugins.moa.two_models_ranking_strategy import TwoModelsRankingStrategy

        # Create a mock strategy instance
        mock_http_client = AsyncMock()
        mock_logger = MagicMock()
        mock_config = MagicMock()
        mock_moa_config = MagicMock()

        strategy = TwoModelsRankingStrategy(mock_http_client, mock_logger, mock_config, mock_moa_config)

        # Valid JSON score
        result = strategy._parse_score('{"score": 0.8}')
        assert result == 0.8

        # Valid JSON score with markdown formatting
        result = strategy._parse_score('```json\n{"score": 0.75}\n```')
        assert result == 0.75

    @pytest.mark.asyncio
    async def test_parse_score_invalid_values(self):
        """Test that invalid scores are handled gracefully."""
        from src.plugins.moa.two_models_ranking_strategy import TwoModelsRankingStrategy

        # Create a mock strategy instance
        mock_http_client = AsyncMock()
        mock_logger = MagicMock()
        mock_config = MagicMock()
        mock_moa_config = MagicMock()

        strategy = TwoModelsRankingStrategy(mock_http_client, mock_logger, mock_config, mock_moa_config)

        # Invalid JSON
        result = strategy._parse_score('invalid json')
        assert result == 0.0

        # Score out of range
        result = strategy._parse_score('{"score": 1.5}')  # Above 1.0
        assert result == 0.0

        result = strategy._parse_score('{"score": -0.5}')  # Below 0.0
        assert result == 0.0

        # Non-numeric score
        result = strategy._parse_score('{"score": "high"}')
