import asyncio
import re
import httpx
from typing import Dict, List, Any, Optional, Union
from collections import defaultdict
from src.shared.base_agent import BaseAgent
from src.shared.config import Config
from src.shared.logging import LoggingManager
from plugins.moa.moa_config import MoAConfigModel
from src.shared.config_manager import ConfigurationManager
from src.plugins.moa.models import ModelResponse, ScoreResult
from src.plugins.moa.ranking_strategy import RankingStrategy
from src.plugins.moa.two_models_ranking_strategy import TwoModelsRankingStrategy
from src.plugins.moa.multi_models_ranking_strategy import MultiModelsRankingStrategy

class MoAAgent(BaseAgent):
    """Mixture of Agents (MoA) agent for enhanced response quality through multi-model consensus."""

    @property
    def name(self) -> str:
        """The name of the agent, used for slash command activation."""
        return "moa"

    def __init__(self):
        self.logger = LoggingManager.get_logger(__name__)
        self.config = Config()
        self.moa_config = ConfigurationManager.get_config(MoAConfigModel, config_path='src/plugins/moa/config.json')

        # Load configuration from MoAConfig
        self.moa_models = self.moa_config.moa_models
        self.timeout = self.moa_config.timeout
        self.max_models = self.moa_config.max_models

        # Validate configuration
        if not self.moa_models:
            raise ValueError("No MoA models configured")

        # Initialize HTTP client for Ollama calls
        self.http_client: httpx.AsyncClient

    def extract_query(self, request: Dict[str, Any]) -> str:
        """Extract the query from the request, removing the /moa command."""
        # Handle chat requests with messages
        messages = request.get('messages', [])
        if messages:
            last_message = messages[-1]
            content = last_message.get('content', '')
        else:
            # Handle generate requests with prompt
            content = request.get('prompt', '')

        # Remove /moa prefix and clean up
        if content.strip().startswith('/moa'):
            query = content.strip()[4:].strip()
            return query

        return content.strip()

    async def on_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process the request through the MoA workflow."""

        query = self.extract_query(request)
        if not query:
            self.logger.warning("MoA activated but no query found")
            return request

        self.logger.info(f"Starting MoA workflow for query: {query[:100]}...")

        try:
            # Initialize HTTP client
            timeout_config = httpx.Timeout(
                connect=self.timeout,
                read=self.timeout,
                write=self.timeout,
                pool=self.timeout
            )
            self.http_client = httpx.AsyncClient(timeout=timeout_config)

            # Limit models to max_models
            models_to_use = self.moa_models[:self.max_models]

            # Stage 1: Collect responses
            stage1_responses = await self.collect_responses(query, models_to_use)
            self.logger.info(f"stage1_responses: {stage1_responses}" )

            if not stage1_responses:
                self.logger.error("No responses collected in Stage 1")
                return self._create_error_response("MoA failed: No responses collected", request)

            # Stage 2: Collect rankings and get best response
            stage2_result = await self.collect_rankings(query, stage1_responses, models_to_use)
            self.logger.info(f"stage2_result: {stage2_result}")

            result = self._create_moa_response(stage2_result, request)
            return result

        except Exception as e:
            self.logger.error(f"MoA workflow failed: {str(e)}", exc_info=True)
            return self._create_error_response(f"MoA process failed: {str(e)}", request)
        finally:
            if self.http_client:
                await self.http_client.aclose()

    async def on_response(self, request: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
        """Optional response processing - not used for MoA."""
        return response

    async def collect_responses(self, query: str, models: List[str]) -> List[Dict[str, str]]:
        """Stage 1: Collect responses from multiple models in parallel."""
        self.logger.info(f"Stage 1: Collecting responses from {len(models)} models")

        async def query_model(model: str) -> Optional[Dict[str, str]]:
            try:
                response = await self._query_ollama(model, query)
                if response:
                    return {"model": model, "response": response}
            except Exception as e:
                self.logger.warning(f"Failed to get response from {model}: {str(e)}")
            return None

        # Query all models in parallel
        tasks = [query_model(model) for model in models]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out failures and None responses
        valid_responses = [result for result in results if result is not None and isinstance(result, dict)]

        self.logger.info(f"Stage 1: Collected {len(valid_responses)} valid responses")
        return valid_responses

    async def _query_ollama(self, model: str, prompt: str) -> Optional[str]:
        """Query Ollama with the given model and prompt."""
        try:
            url = f"{self.config.ollama_host}:{self.config.ollama_port}/api/chat"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }

            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            return data.get("message", {}).get("content", "")

        except Exception as e:
            self.logger.error(f"Failed to query Ollama with model {model}: {str(e)}")
            return None

    async def collect_rankings(self, query: str, responses: List[Dict[str, str]], models: List[str]) -> str:
        """Stage 2: Collect rankings using appropriate strategy based on model count."""
        self.logger.info(f"Stage 2: Collecting scores from {len(models)} models")

        if len(responses) <= 1:
            # With only one response, score is perfect
            return responses[0]["response"]

        # Select strategy based on number of models
        if len(models) <= 2:
            strategy = TwoModelsRankingStrategy(self.http_client, self.logger, self.config, self.moa_config)
        else:
            strategy = MultiModelsRankingStrategy(self.http_client, self.logger, self.config, self.moa_config)

        # Use the strategy to collect rankings
        best_response = await strategy.collect_rankings(query, responses, models)
        return best_response

    def _create_response(self, content: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create a properly formatted Ollama-compatible response."""
        # Check if this is a chat request or generate request
        if 'messages' in request:
            # Chat response format
            return {
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "done": True
            }
        else:
            # Generate response format
            return {
                "response": content,
                "done": True
            }

    def _create_moa_response(self, content: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create a properly formatted Ollama-compatible response."""
        return self._create_response(content, request)

    def _create_error_response(self, error_message: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create an error response."""
        return self._create_response(error_message, request)