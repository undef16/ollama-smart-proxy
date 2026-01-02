from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Union, Iterator
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

    async def generate(self, request: GenerateRequest) -> Union[Any, StreamingResponse]:
        """Handle generate requests and forward to Ollama."""
        try:
            self.logger.info(f"Generate router - Processing generate request for model: {request.model}")
            response = await self.generate_chain.process_generate_request(request)
            self.logger.info(f"Generate router - Generate request processed successfully for model: {request.model}")

            # Check if response is a generator (streaming)
            # Handle different types of generators and iterables
            if hasattr(response, '__iter__') and not isinstance(response, (str, bytes, dict, list)):
                # Streaming response - handle various generator types
                async def generate():
                    try:
                        for chunk in response:
                            # Ensure chunk is a dictionary before JSON serialization
                            if isinstance(chunk, dict):
                                yield json.dumps(chunk, ensure_ascii=False) + "\n"
                            else:
                                # Handle non-dict chunks by wrapping them
                                yield json.dumps({"response": str(chunk), "done": False}) + "\n"
                    except Exception as e:
                        self.logger.error(f"Error in streaming generation: {str(e)}")
                        # Send error chunk
                        yield json.dumps({"error": str(e), "done": True}) + "\n"
                
                return StreamingResponse(
                    generate(), 
                    media_type="application/x-ndjson",
                    headers={"Cache-Control": "no-cache"}
                )
            else:
                # Non-streaming response
                return response
        except Exception as e:
            self.logger.error(f"Error processing generate request: {str(e)}")
            raise HTTPException(status_code=HTTP_ERROR, detail="Internal server error")