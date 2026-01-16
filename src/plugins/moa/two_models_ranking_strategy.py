import asyncio
from typing import Dict, List
from collections import defaultdict
from src.plugins.moa.ranking_strategy import RankingStrategy

class TwoModelsRankingStrategy(RankingStrategy):
    """Concrete strategy for 2 models using circular evaluation."""

    async def collect_rankings(self, query: str, responses: List[Dict[str, str]], models: List[str]) -> str:
        """Collect rankings using circular evaluation for 2 models."""
        self.logger.info(f"Using TwoModelsRankingStrategy for {len(models)} models")

        # Create tasks for circular evaluation
        tasks = []
        for i, evaluator in enumerate(models):
            target_index = (i - 1) % len(models)
            target_response = responses[target_index]["response"]
            tasks.append(self._score_response(evaluator, query, target_response))

        # Execute all scoring tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect scores
        scores = defaultdict(list)
        for i in range(len(models)):
            target_index = (i - 1) % len(models)
            response = responses[target_index]["response"]
            score = results[i] if not isinstance(results[i], Exception) else 0.0
            scores[response].append(score)

        # Find best response
        best_response = ""
        best_score = -1.0
        for response, score_list in scores.items():
            if not score_list:
                continue
            avg_score = score_list[0]  # For 2 models, use single score
            if avg_score > best_score:
                best_score = avg_score
                best_response = response

        return best_response

    async def _score_response(self, evaluator_model: str, query: str, target_response: str) -> float:
        """Score a response using the evaluator model."""
        try:
            prompt = self._build_scoring_prompt(query, target_response)
            score_text = await self._query_ollama(evaluator_model, prompt)
            if score_text:
                score = self._parse_score(score_text)
                return score
        except Exception as e:
            self.logger.error(f"Failed to get score from {evaluator_model}: {str(e)}", stack_info=True)
        return 0.0
