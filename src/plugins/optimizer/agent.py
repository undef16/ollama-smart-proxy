"""Optimizer Agent for dynamic LLM parameter optimization."""

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional

from src.shared.base_agent import BaseAgent
from src.shared.logging import LoggingManager

from .db_utils import DatabaseManager
from .simhash_utils import TemplateMatcher
from .const import AGENT_NAME, SAFETY_MARGIN


@dataclass
class OptimizerMetadata:
    """Metadata for optimizer operations."""

    template_id: Optional[int] = None
    confidence: Optional[float] = None
    distance: Optional[int] = None
    reasoning: Optional[str] = None


class OptimizerAgent(BaseAgent):
    """Intelligent agent for optimizing LLM inference parameters."""

    def __init__(self):
        """Initialize the optimizer agent."""
        self.logger = LoggingManager.get_logger(__name__)

        # Database setup
        plugin_dir = Path(__file__).parent
        db_path = plugin_dir / "data" / "optimizer_stats.db"
        db_path.parent.mkdir(exist_ok=True)
        self.db = DatabaseManager(db_path)

        # Template matcher
        self.matcher = TemplateMatcher(self.db)

        self.logger.info("OptimizerAgent initialized")

    @property
    def name(self) -> str:
        """The name of the agent, used for slash command activation."""
        return AGENT_NAME

    async def on_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process the request context before sending to Ollama.

        Args:
            request: Request context dictionary containing request data.

        Returns:
            Modified request dictionary.
        """
        if not isinstance(request, dict):
            self.logger.warning("Invalid request type, skipping optimization")
            return request

        try:
            start_time = time.time()

            # Extract and validate prompt text
            prompt_text = self._extract_prompt_text(request)
            if not prompt_text or not prompt_text.strip():
                self.logger.debug("No valid prompt text found, skipping optimization")
                return request

            # Find matching template asynchronously
            match = await self._find_matching_template_async(prompt_text)

            if match:
                await self._apply_template_match(request, match)

            processing_time = time.time() - start_time
            self.logger.debug(f"Request processing completed in {processing_time:.3f}s")

        except Exception as e:
            self.logger.error(f"Error in on_request: {e}", stack_info=True)
            # Continue with original request

        return request

    async def on_response(self, request: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
        """Process the response after receiving from Ollama.

        Args:
            request: Request context dictionary.
            response: Response dictionary from Ollama.

        Returns:
            Modified response dictionary.
        """
        if not isinstance(request, dict) or not isinstance(response, dict):
            self.logger.warning("Invalid request or response type")
            return response

        try:
            # Calculate working window from actual token usage
            prompt_eval_count = response.get("prompt_eval_count")
            eval_count = response.get("eval_count")

            if self._is_valid_token_counts(prompt_eval_count, eval_count):
                total_tokens = int(prompt_eval_count) + int(eval_count)  # type: ignore
                working_window = int(total_tokens * SAFETY_MARGIN)

                # Check if we matched a template in on_request
                optimizer_meta = request.get("_optimizer")
                if optimizer_meta and isinstance(optimizer_meta, OptimizerMetadata):
                    await self._update_existing_template(optimizer_meta, working_window)
                else:
                    await self._learn_new_template(request, working_window)

        except Exception as e:
            self.logger.error(f"Error in on_response: {e}")

        return response

    def _extract_prompt_text(self, request: Dict[str, Any]) -> Optional[str]:
        """Extract prompt text from request, including full conversation with roles.

        Args:
            request: Request dictionary.

        Returns:
            Extracted prompt text or None.
        """
        # Handle chat messages - concatenate all messages with roles
        if "messages" in request:
            messages = request["messages"]
            if isinstance(messages, list) and messages:
                # Build full conversation text with roles
                conversation_parts = []
                for msg in messages:
                    if isinstance(msg, dict):
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")
                        if isinstance(content, str):
                            conversation_parts.append(f"{role}: {content}")
                if conversation_parts:
                    return "\n".join(conversation_parts)

        # Handle generate prompt
        if "prompt" in request:
            prompt = request["prompt"]
            if isinstance(prompt, str):
                return prompt

        return None

    def _apply_optimizations(self, request: Dict[str, Any], working_window: Optional[int]) -> None:
        """Apply parameter optimizations to request.

        Args:
            request: Request dictionary to modify.
            working_window: Optimal context window size.
        """
        # Initialize options if not present
        if "options" not in request:
            request["options"] = {}

        options = request["options"]
        if not isinstance(options, dict):
            options = {}
            request["options"] = options

        # Set context window
        if working_window and isinstance(working_window, int) and working_window > 0:
            options["num_ctx"] = working_window
            self.logger.debug(f"Applied optimizations: num_ctx={working_window}")
        else:
            self.logger.debug("No valid working window to apply")

    async def _find_matching_template_async(self, prompt_text: str) -> Optional[Dict[str, Any]]:
        """Asynchronously find matching template.

        Args:
            prompt_text: Text to match.

        Returns:
            Match dictionary or None.
        """
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, self.matcher.find_matching_template, prompt_text)
        except Exception as e:
            self.logger.error(f"Error finding matching template: {e}")
            return None

    async def _apply_template_match(self, request: Dict[str, Any], match: Dict[str, Any]) -> None:
        """Apply template match optimizations.

        Args:
            request: Request to modify.
            match: Match information.
        """
        template = match.get("template")
        if not template:
            return

        working_window = getattr(template, "working_window", None)
        resolution = match.get("resolution")
        distance = match.get("distance")

        self.logger.info(
            f"Matched template {template.id} at resolution {resolution}, "
            f"distance {distance}, applying window {working_window}"
        )

        # Apply optimizations
        self._apply_optimizations(request, working_window)

        # Store metadata
        request["_optimizer"] = OptimizerMetadata(
            template_id=template.id,
            confidence=match.get("score"),
            distance=distance,
            reasoning=f"Matched template at resolution {resolution}",
        )

    def _is_valid_token_counts(self, prompt_eval_count: Any, eval_count: Any) -> bool:
        """Validate token counts.

        Args:
            prompt_eval_count: Prompt evaluation token count.
            eval_count: Evaluation token count.

        Returns:
            True if valid.
        """
        return (
            isinstance(prompt_eval_count, int)
            and prompt_eval_count >= 0
            and isinstance(eval_count, int)
            and eval_count >= 0
        )

    async def _update_existing_template(self, optimizer_meta: OptimizerMetadata, working_window: int) -> None:
        """Update existing template with new data.

        Args:
            optimizer_meta: Optimizer metadata.
            working_window: New working window.
        """
        template_id = optimizer_meta.template_id
        distance = optimizer_meta.distance

        if template_id is not None and distance is not None:
            loop = asyncio.get_event_loop()
            try:
                await loop.run_in_executor(None, self.db.update_template, template_id, distance, working_window, 32)  # Default batch size of 32 when not specified
                self.logger.debug(f"Updated template {template_id} with working_window {working_window}")
            except Exception as e:
                self.logger.error(f"Error updating template {template_id}: {e}")

    async def _learn_new_template(self, request: Dict[str, Any], working_window: int) -> None:
        """Learn new template from request.

        Args:
            request: Request dictionary.
            working_window: Working window size.
        """
        prompt_text = self._extract_prompt_text(request)
        if prompt_text and prompt_text.strip():
            loop = asyncio.get_event_loop()
            try:
                template_id = await loop.run_in_executor(None, self.matcher.learn_template, prompt_text, working_window, 32)  # Default batch size of 32
                self.logger.debug(f"Learned new template {template_id} with working_window {working_window}")
            except Exception as e:
                self.logger.error(f"Error learning new template: {e}")
