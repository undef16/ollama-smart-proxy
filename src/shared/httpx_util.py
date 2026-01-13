"""HTTP utilities for the Ollama Smart Proxy."""

import httpx
from fastapi import HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from typing import Union, Optional
import json
from .config import Config
from .logging import LoggingManager
from src.const import HTTP_BAD_REQUEST, HTTP_ERROR, CONTENT_TYPE_HEADER, CONTENT_TYPE_JSON


class HTTPX_Util:
    
    @staticmethod
    def generic_passthrough(request: Request, path: str, ollama_host: Optional[str] = None, ollama_port: Optional[int] = None) -> Union[Response, StreamingResponse]:
        """Generic passthrough function that can be used independently across the application."""
        try:
            config = Config()
            # Use provided host/port or fall back to config
            host = ollama_host or config.ollama_host
            port = ollama_port or config.ollama_port
            url = f"{host}:{port}/api/{path}"
            
            # Get the request body properly with JSON support
            import asyncio
            try:
                # Check if the content type is JSON
                content_type = request.headers.get(CONTENT_TYPE_HEADER, "")
                
                if CONTENT_TYPE_JSON in content_type.lower():
                    # Handle JSON data properly
                    body_bytes = asyncio.run(request.body())
                    if body_bytes:
                        json_data = json.loads(body_bytes.decode('utf-8'))
                        body = json_data
                        # Check if this is a streaming request based on the JSON body
                        is_streaming = json_data.get('stream', False)
                    else:
                        body = {}
                        is_streaming = False
                else:
                    # Keep the original behavior for non-JSON content
                    body = asyncio.run(request.body())
                    is_streaming = False
                    
            except json.JSONDecodeError as je:
                logger = LoggingManager.get_logger(__name__)
                logger.error(f"Error decoding JSON: {str(je)}", stack_info=True)
                raise HTTPException(status_code=HTTP_BAD_REQUEST, detail="Invalid JSON in request body")
            except Exception as e:
                # Fallback for any other errors
                body = b""
                is_streaming = False
            
            # Check if this is a streaming request based on path or body
            is_streaming = is_streaming or "stream" in path
            
            if is_streaming:
                # For streaming, we need to use httpx stream client
                def stream_response():
                    with httpx.stream(request.method, url, headers=request.headers, json=body if isinstance(body, dict) else None, content=body if not isinstance(body, dict) else None) as response:
                        for chunk in response.iter_bytes():
                            yield chunk
                
                return StreamingResponse(stream_response(), media_type="text/plain")
            else:
                with httpx.Client() as client:
                    response = client.request(
                        request.method,
                        url,
                        headers=request.headers,
                        json=body if isinstance(body, dict) else None,
                        content=body if not isinstance(body, dict) else None
                    )
                
                    return Response(
                        content=response.content,
                        status_code=response.status_code,
                        headers=dict(response.headers)
                    )
                
        except Exception as e:
            logger = LoggingManager.get_logger(__name__)
            logger.error(f"Error in generic passthrough: {str(e)}", stack_info=True)
            raise HTTPException(status_code=HTTP_ERROR, detail="Passthrough request failed")