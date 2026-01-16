import asyncio
import httpx
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from collections import defaultdict
from src.shared.config import Config
from src.plugins.moa.moa_config import MoAConfigModel

class RankingStrategy(ABC):
    """Abstract base class for ranking strategies."""

    def __init__(self, http_client: httpx.AsyncClient, logger: Any, config: Config, moa_config: MoAConfigModel):
        self.http_client = http_client
        self.logger = logger
        self.config = config
        self.moa_config = moa_config

    @abstractmethod
    async def collect_rankings(self, query: str, responses: List[Dict[str, str]], models: List[str]) -> str:
        """Collect rankings using the specific strategy."""
        pass

    def _build_scoring_prompt(self, query: str, previous_response: str) -> str:
        """Build the scoring prompt for evaluation."""
        scoring_prompt_template = self.moa_config.prompts.get('ranking_prompt')
        if not scoring_prompt_template:
            raise ValueError("Scoring prompt not found in configuration")
        return scoring_prompt_template.format(query=query, previous_response=previous_response)

    def _parse_score(self, score_text: str) -> float:
        """Parse the score from model response."""
        try:
            import json
            import re
            # Clean markdown code blocks if present
            cleaned_text = re.sub(r'^```json\s*', '', score_text)
            cleaned_text = re.sub(r'```\s*$', '', cleaned_text)
            cleaned_text = cleaned_text.strip()
            data = json.loads(cleaned_text)
            score = data.get('score')
            if isinstance(score, (int, float)) and 0 <= score <= 1:
                return float(score)
            else:
                self.logger.warning(f"Invalid score value: {score}")
                return 0.0
        except Exception as e:
            self.logger.warning(f"Failed to parse score from response: {score_text}, error: {str(e)}")
            return 0.0

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
