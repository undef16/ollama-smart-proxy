import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List

from shared.logging import LoggingManager
from src.const import HTTP_BAD_REQUEST, HTTP_ERROR, MODEL_FIELD, PROMPT_FIELD, STREAM_FIELD, CONTENT_TYPE_HEADER, CONTENT_TYPE_JSON, HOST_HEADER


class PassthroughRouter:
    """Router for passthrough endpoints."""

    def __init__(self, ollama_client):
        self.ollama_client = ollama_client
        self.router = APIRouter(tags=["passthrough"])
        self.logger = LoggingManager.get_logger(__name__)
        self.router.post("/api/generate")(self.generate)
        self.router.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])(self.generic_passthrough)

    @classmethod
    def get_router(cls, ollama_client) -> APIRouter:
        """Get the router instance."""
        return cls(ollama_client).router

    def _validate_required_fields(self, request: Dict[str, Any], fields: List[str]):
        """Validate that required fields are present in the request."""
        for field in fields:
            if not request.get(field):
                raise HTTPException(status_code=HTTP_BAD_REQUEST, detail=f"{field} is required")

    def _extract_kwargs(self, request: Dict[str, Any], exclude_fields: List[str]) -> Dict[str, Any]:
        """Extract kwargs from request excluding specified fields."""
        return {k: v for k, v in request.items() if k not in exclude_fields}

    async def generate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate text using Ollama."""
        try:
            self._validate_required_fields(request, [MODEL_FIELD, PROMPT_FIELD])
            model = request[MODEL_FIELD]
            prompt = request[PROMPT_FIELD]
            stream = request.get(STREAM_FIELD, False)
            kwargs = self._extract_kwargs(request, [MODEL_FIELD, PROMPT_FIELD, STREAM_FIELD])
    
            self.logger.info(f"Generating text with model: {model}")
            result = await self.ollama_client.generate(
                model=model,
                prompt=prompt,
                stream=stream,
                **kwargs
            )
            self.logger.info(f"Text generation completed for model: {model}")
            return result
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error generating text: {str(e)}")
            raise HTTPException(status_code=HTTP_ERROR, detail="Text generation failed")

    async def generic_passthrough(self, request: Request, path: str):
        """Generic passthrough for any Ollama API request."""
        try:
            from shared.config import Config
            config = Config()
            url = f"{config.ollama_host}:{config.ollama_port}/api/{path}"
            async with httpx.AsyncClient() as client:
                body = await request.body()
                json_data = None
                if request.headers.get(CONTENT_TYPE_HEADER) == CONTENT_TYPE_JSON and body:
                    json_data = await request.json()
                headers = {k: v for k, v in request.headers.items() if k.lower() not in [HOST_HEADER]}
                response = await client.request(
                    request.method,
                    url,
                    json=json_data,
                    headers=headers,
                    content=body if not json_data else None
                )
                return StreamingResponse(
                    response.aiter_bytes(),
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
        except Exception as e:
            self.logger.error(f"Error in generic passthrough: {str(e)}")
            raise HTTPException(status_code=HTTP_ERROR, detail="Passthrough request failed")
