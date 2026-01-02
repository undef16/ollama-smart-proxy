from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Union
import json

from shared.logging import LoggingManager
from .agent_chain import GenerateChain, GenerateRequest
from src.const import HTTP_ERROR


class GenerateRouter:
    """Router for generate endpoints."""

    def __init__(self, registry, ollama_client):

        self.logger = LoggingManager.get_logger(__name__)
        self.generate_chain = GenerateChain(registry, ollama_client)

        self.router = APIRouter(tags=["generate"])
        self.router.post("/api/generate", response_model=None)(self.generate)

    @classmethod
    def get_router(cls, registry, ollama_client) -> APIRouter:
        """Get the router instance."""
        return cls(registry, ollama_client).router

    async def generate(self, request: GenerateRequest) -> Union[Dict[str, Any], StreamingResponse]:
        """Handle generate requests and forward to Ollama."""
        try:
            self.logger.info(f"Generate router - Processing generate request for model: {request.model}")
            response = await self.generate_chain.process_generate_request(request)
            self.logger.info(f"Generate router - Generate request processed successfully for model: {request.model}")

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
            self.logger.error(f"Error processing generate request: {str(e)}")
            raise HTTPException(status_code=HTTP_ERROR, detail="Internal server error")