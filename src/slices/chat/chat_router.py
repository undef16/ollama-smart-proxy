from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Union, Iterator

from shared.logging import LoggingManager
from ..base_router import BaseRouter
from .chat_agent_chain import ChatAgentChain
from src.const import HTTP_ERROR, RESPONSE_FIELD, DONE_FIELD, ERROR_FIELD, STREAMING_MEDIA_TYPE, CACHE_CONTROL_NO_CACHE


class ChatRouter(BaseRouter):
    """Router for chat endpoints."""

    chain_class = ChatAgentChain
    tag = "chat"

    def __init__(self, registry):
        super().__init__(registry)
        self.logger = LoggingManager.get_logger(__name__)

    def add_routes(self):
        self.router.post("/api/chat", response_model=None)(self.chat)

    @classmethod
    def get_router(cls, registry) -> APIRouter:
        """Get the router instance."""
        return cls(registry).router

    async def chat(self, request: Request) -> Union[Any, StreamingResponse]:
        """Handle chat requests and forward to Ollama."""
        try:
            self.logger.info("Chat router - Starting to read request body")
            # Get the request body properly
            data = await request.json()
            self.logger.info("Chat router - Body read and parsed successfully")
            # self.logger.info(f"Chat router - Request messages: {data['messages']}")
            response = await self.chain.process_request(data)
            return response
        except Exception as e:
            self.logger.error(f"Error processing chat request: {str(e)}")
            raise HTTPException(status_code=HTTP_ERROR, detail="Internal server error")