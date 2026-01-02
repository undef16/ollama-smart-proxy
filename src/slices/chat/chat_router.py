from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Union
import json

from shared.logging import LoggingManager
from .agent_chain import AgentChain, ChatRequest
from src.const import HTTP_ERROR


class ChatRouter:
    """Router for chat endpoints."""

    def __init__(self, registry, ollama_client):
        
        self.logger = LoggingManager.get_logger(__name__)
        self.agent_chain = AgentChain(registry, ollama_client)

        self.router = APIRouter(tags=["chat"])
        self.router.post("/api/chat", response_model=None)(self.chat)
        
        # self.router = APIRouter(prefix="/api/chat", tags=["chat"])
        # self.router.post("/")(self.chat)

    @classmethod
    def get_router(cls, registry, ollama_client) -> APIRouter:
        """Get the router instance."""
        return cls(registry, ollama_client).router

    async def chat(self, request: ChatRequest) -> Union[Dict[str, Any], StreamingResponse]:
        """Handle chat requests and forward to Ollama."""
        try:
            self.logger.info(f"Chat router - Processing chat request for model: {request.model}")
            # self.logger.info(f"Chat router - Request messages: {request.messages}")
            response = await self.agent_chain.process_chat_request(request)
            self.logger.info(f"Chat router - Chat request processed successfully for model: {request.model}")

            # Check if response is a generator (streaming)
            if hasattr(response, '__iter__') and hasattr(response, '__next__'):
                # Streaming response
                async def generate():
                    for chunk in response:
                        yield json.dumps(chunk) + "\n"
                return StreamingResponse(generate(), media_type="application/json")
            else:
                # Non-streaming response
                return response
        except Exception as e:
            self.logger.error(f"Error processing chat request: {str(e)}")
            raise HTTPException(status_code=HTTP_ERROR, detail="Internal server error")