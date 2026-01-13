import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Union, Iterator
import json

from shared.logging import LoggingManager
from ..base_router import BaseRouter
from .generate_agent_chain import GenerateAgentChain
from src.const import HTTP_ERROR, RESPONSE_FIELD, DONE_FIELD, ERROR_FIELD, STREAMING_MEDIA_TYPE, CACHE_CONTROL_NO_CACHE, MODEL_FIELD, PROMPT_FIELD, STREAM_FIELD, AGENTS_FIELD


class GenerateRouter(BaseRouter):
    """Router for generate endpoints."""

    chain_class = GenerateAgentChain
    tag = "generate"

    def __init__(self, registry):
        super().__init__(registry)
        self.logger = LoggingManager.get_logger(__name__)

    def add_routes(self):
        self.router.post("/api/generate", response_model=None)(self.generate)

    @classmethod
    def get_router(cls, registry) -> APIRouter:
        """Get the router instance."""
        return cls(registry).router

    async def generate(self, request: Dict[str, Any]) -> Union[Any, StreamingResponse]:
        """Handle generate requests and forward to Ollama."""
        try:
            response = await self.chain.process_request(request)
            return response
        except Exception as e:
            self.logger.error(f"Error processing generate request: {str(e)}", stack_info=True)
            raise HTTPException(status_code=HTTP_ERROR, detail="Internal server error")