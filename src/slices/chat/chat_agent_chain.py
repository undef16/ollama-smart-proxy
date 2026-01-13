"""Chat processing logic for the Ollama Smart Proxy."""

from typing import Any, Dict, List

from pydantic import BaseModel
from slices.base_chain import BaseChain

# from .base_chain import BaseChain
from src.const import MESSAGE_FIELD, CONTENT_FIELD, USER_ROLE, MODEL_FIELD, MESSAGES_FIELD, STREAM_FIELD, AGENTS_FIELD, NO_CONTENT_PLACEHOLDER


class Message(BaseModel):
    """A chat message."""

    role: str
    content: str


class ChatAgentChain(BaseChain):
    """Handles chat request processing and Ollama forwarding."""

    def get_ollama_endpoint(self) -> str:
        return "/api/chat"

    def prepare_context(self, request: Dict[str, Any]) -> Dict[str, Any]:
        model = request['model']
        messages = request['messages']
        self.logger.info(f"Processing chat request for model: {model}")
        return {
            MODEL_FIELD: model,
            MESSAGES_FIELD: messages,
            STREAM_FIELD: request.get('stream', False)
        }

    def get_content_for_agent_parsing(self, request: Dict[str, Any]) -> str:
        messages = request.get('messages', [])
        if messages and messages[-1].get("role") == USER_ROLE:
            content = messages[-1].get("content", "")
            self.logger.info(f"Processing user message: {content}")
            return content
        return ""

    def update_content_in_context(self, context: Dict[str, Any], cleaned_content: str):
        messages = context.get(MESSAGES_FIELD, [])
        if messages and messages[-1].get("role") == USER_ROLE:
            messages[-1]["content"] = cleaned_content

    def build_ollama_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'model': context[MODEL_FIELD],
            'messages': context[MESSAGES_FIELD],
            'stream': context.get(STREAM_FIELD, False)
        }

    def create_response_context(self, response_data: Dict[str, Any], agents: List[str]) -> Dict[str, Any]:
        return {
            MESSAGE_FIELD: response_data,
            AGENTS_FIELD: agents
        }

    def get_response_key(self) -> str:
        return MESSAGE_FIELD

    def get_content_path(self) -> List[str]:
        return [MESSAGE_FIELD, CONTENT_FIELD]

    def get_final_key(self) -> str:
        return MESSAGE_FIELD

