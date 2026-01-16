import asyncio
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass
from src.plugins.moa.ranking_strategy import RankingStrategy

class MultiModelsRankingStrategy(RankingStrategy):
    """Concrete strategy for 3+ models using n+1/n+2 evaluation."""

    async def collect_rankings(self, query: str, responses: List[Dict[str, str]], models: List[str]) -> str:
        """Collect rankings using n+1/n+2 evaluation for 3+ models.
        
        Args:
            query: The input query string
            responses: List of response dictionaries containing 'response' keys
            models: List of model names to use for evaluation
            
        Returns:
            The best response based on evaluation scores
        """
        self.logger.info(f"Using MultiModelsRankingStrategy for {len(models)} models")

        # Group scoring requests by evaluator model to minimize API calls
        batch_results = await self._extract_batch_result(query, responses, models)

        # Collect scores from batch results
        scores = self._get_scores(responses, batch_results)

        # Find best response
        best_response = self._get_best_response(scores)

        return best_response

    def _get_best_response(self, scores):
        best_response = ""
        best_score = -1.0
        for response, score_list in scores.items():
            if not score_list:
                continue
            avg_score = sum(score_list) / len(score_list)  # Average for multiple scores
            if avg_score > best_score:
                best_score = avg_score
                best_response = response
        return best_response

    def _get_scores(self, responses, batch_results):
        scores = defaultdict(list)
        for eval_idx, result in enumerate(batch_results):
            if isinstance(result, Exception):
                self.logger.error(f"Batch scoring failed for evaluator {eval_idx}: {str(result)}")
                continue
            
            # result is a list of {response_id, score} dictionaries
            if isinstance(result, list):
                for item in result:
                    response_id = item['response_id']
                    score = item['score']
                    if response_id < len(responses):
                        response_text = responses[response_id]["response"]
                        scores[response_text].append(score)
        return scores

    async def _extract_batch_result(self, query, responses, models):
        evaluation_tasks = []
        num_models = len(models)
        
        for evaluator_idx, evaluator_model in enumerate(models):
            # Determine which responses this evaluator should score
            # Each evaluator scores the responses that are not their own and not the immediate previous
            responses_to_score = []
            
            for target_idx in range(len(responses)):
                # In the n+1/n+2 approach, each response is evaluated by the next 2 models
                # So for each evaluator, find which responses they are supposed to evaluate
                # An evaluator at index E evaluates responses from indices where:
                # E == (target_idx + 1) % num_models or E == (target_idx + 2) % num_models
                if evaluator_idx == (target_idx + 1) % num_models or evaluator_idx == (target_idx + 2) % num_models:
                    responses_to_score.append({
                        'id': target_idx,
                        'response': responses[target_idx]["response"]
                    })
            
            if responses_to_score:
                # Build a batch prompt with multiple responses to score
                evaluation_tasks.append(
                    self._score_responses_batch(evaluator_model, query, responses_to_score)
                )

        # Execute all batch scoring tasks in parallel
        batch_results = await asyncio.gather(*evaluation_tasks, return_exceptions=True)
        return batch_results

    async def _score_responses_batch(self, evaluator_model: str, query: str, responses_to_score: List[Dict]) -> List[Dict]:
        """Score multiple responses in a single batch request."""
        try:
            prompt = self._build_batch_scoring_prompt(query, responses_to_score)
            score_text = await self._query_ollama(evaluator_model, prompt)
            if score_text:
                scores = self._parse_batch_scores(score_text, responses_to_score)
                return scores
        except Exception as e:
            self.logger.error(f"Failed to get batch scores from {evaluator_model}: {str(e)}", stack_info=True)
        # Return empty list if there's an error
        return []

    def _build_batch_scoring_prompt(self, query: str, responses_to_score: List[Dict]) -> str:
        """Build the batch scoring prompt for evaluation.
        
        Args:
            query: The input query string
            responses_to_score: List of response dictionaries with 'id' and 'response' keys
            
        Returns:
            Formatted prompt string for batch scoring
            
        Raises:
            ValueError: If no suitable prompt template is found in configuration
        """
        batch_scoring_prompt_template = self.moa_config.prompts.get('batch_ranking_prompt')
        if not batch_scoring_prompt_template:
            # Fallback to regular ranking prompt if batch prompt not available
            batch_scoring_prompt_template = self.moa_config.prompts.get('ranking_prompt')
            if not batch_scoring_prompt_template:
                raise ValueError("Batch scoring prompt not found in configuration")
        
        # Format responses for the prompt
        formatted_responses = "\n".join(
            f"Response {i}: {response_data['response']}"
            for i, response_data in enumerate(responses_to_score)
        )
        
        return batch_scoring_prompt_template.format(query=query, responses=formatted_responses)

    def _parse_batch_scores(self, score_text: str, responses_to_score: List[Dict]) -> List[Dict]:
        """Parse the batch scores from model response.

        Args:
            score_text: Raw text response from the model containing JSON scores
            responses_to_score: List of response dictionaries with 'id' and 'response' keys

        Returns:
            List of dictionaries containing 'response_id' and 'score' keys with original indices
        """
        try:
            import json
            import re
            # Clean markdown code blocks if present
            cleaned_text = re.sub(r'^```json\s*', '', score_text)
            cleaned_text = re.sub(r'```\s*$', '', cleaned_text)
            cleaned_text = cleaned_text.strip()
            data = json.loads(cleaned_text)

            # Expect a list of objects with response_id and score
            if isinstance(data, list):
                scores = []
                for item in data:
                    if isinstance(item, dict) and 'response_id' in item and 'score' in item:
                        response_id = int(item['response_id'])
                        score = item['score']
                        if isinstance(score, (int, float)) and 0 <= score <= 1 and 0 <= response_id < len(responses_to_score):
                            # Map response_id (index in responses_to_score) to original response index
                            original_response_id = responses_to_score[response_id]['id']
                            scores.append({
                                'response_id': original_response_id,
                                'score': float(score)
                            })
                        else:
                            self.logger.warning(f"Invalid score data: response_id={response_id}, score={score}")
                return scores
            else:
                self.logger.warning(f"Expected list of scores, got: {type(data)}")
                return []
        except Exception as e:
            self.logger.warning(f"Failed to parse batch scores from response: {score_text}, error: {str(e)}")
            return []