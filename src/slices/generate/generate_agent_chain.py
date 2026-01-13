"""Generate processing logic for the Ollama Smart Proxy."""

from typing import Any, Dict, List

from slices.base_chain import BaseChain


from src.const import RESPONSE_FIELD, MODEL_FIELD, PROMPT_FIELD, STREAM_FIELD, AGENTS_FIELD, NO_RESPONSE_PLACEHOLDER


class GenerateAgentChain(BaseChain):
    """Handles generate request processing and Ollama forwarding."""

    def get_ollama_endpoint(self) -> str:
        return "/api/generate"

    def prepare_context(self, request: Dict[str, Any]) -> Dict[str, Any]:
        model = request['model']
        prompt = request['prompt']
        self.logger.info(f"Processing generate request for model: {model}")
        return {
            MODEL_FIELD: model,
            PROMPT_FIELD: prompt,
            STREAM_FIELD: request.get('stream', False)
        }

    def get_content_for_agent_parsing(self, request: Dict[str, Any]) -> str:
        prompt = request.get('prompt', '')
        self.logger.info(f"Parsed prompt: {prompt}")
        return prompt

    def update_content_in_context(self, context: Dict[str, Any], cleaned_content: str):
        context[PROMPT_FIELD] = cleaned_content

    def build_ollama_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'model': context[MODEL_FIELD],
            'prompt': context[PROMPT_FIELD],
            'stream': context.get(STREAM_FIELD, False)
        }

    def create_response_context(self, response_data: Dict[str, Any], agents: List[str]) -> Dict[str, Any]:
        return {
            RESPONSE_FIELD: response_data,
            AGENTS_FIELD: agents
        }

    def get_response_key(self) -> str:
        return RESPONSE_FIELD

    def get_content_path(self) -> List[str]:
        return [RESPONSE_FIELD]

    def get_final_key(self) -> str:
        return RESPONSE_FIELD

