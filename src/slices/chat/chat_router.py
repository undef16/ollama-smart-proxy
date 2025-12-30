from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from shared.logging import LoggingManager
from .agent_chain import AgentChain, ChatRequest


class ChatRouter:
    """Router for chat endpoints."""

    def __init__(self, registry, ollama_client):
        
        self.logger = LoggingManager.get_logger(__name__)
        self.agent_chain = AgentChain(registry, ollama_client)

        self.router = APIRouter(tags=["chat"])
        self.router.post("/api/chat")(self.chat)
        
        # self.router = APIRouter(prefix="/api/chat", tags=["chat"])
        # self.router.post("/")(self.chat)

    @classmethod
    def get_router(cls, registry, ollama_client) -> APIRouter:
        """Get the router instance."""
        return cls(registry, ollama_client).router

    async def chat(self, request: ChatRequest) -> Dict[str, Any]:
        """Handle chat requests and forward to Ollama."""
        try:
            self.logger.info(f"Chat router - Processing chat request for model: {request.model}")
            self.logger.info(f"Chat router - Request messages: {request.messages}")
            response = await self.agent_chain.process_chat_request(request)
            self.logger.info(f"Chat router - Chat request processed successfully for model: {request.model}")
            return response
        except Exception as e:
            self.logger.error(f"Error processing chat request: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")