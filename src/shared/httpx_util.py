"""HTTP utilities for the Ollama Smart Proxy."""

import httpx
from fastapi import HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from typing import Union, Optional
import json
import asyncio
from .config import Config
from .logging import LoggingManager
from src.const import HTTP_BAD_REQUEST, HTTP_ERROR, CONTENT_TYPE_HEADER, CONTENT_TYPE_JSON, OLLAMA_REQUEST_TIMEOUT


class HTTPX_Util:
    
    @staticmethod
    def generic_passthrough(request: Request, path: str, ollama_host: Optional[str] = None, ollama_port: Optional[int] = None) -> Union[Response, StreamingResponse]:
        """Generic passthrough function that can be used independently across the application."""
        try:
            config = Config()
            url = f"{(ollama_host or config.ollama_host)}:{(ollama_port or config.ollama_port)}/api/{path}"

            # Parse request body and determine streaming behavior
            body, is_streaming = HTTPX_Util._parse_request_body(request, path)

            # Clean headers to prevent Content-Length conflicts
            headers = {k: v for k, v in request.headers.items() if k.lower() not in ('content-length', 'transfer-encoding')}

            if is_streaming:
                return HTTPX_Util._handle_streaming_request(request.method, url, headers, body)
            else:
                return HTTPX_Util._handle_regular_request(request.method, url, headers, body)

        except httpx.ConnectError as e:
            logger = LoggingManager.get_logger(__name__)
            logger.error(f"Failed to connect to Ollama in passthrough: {str(e)}", stack_info=True)
            raise HTTPException(status_code=HTTP_ERROR, detail=f"Failed to connect to Ollama: {str(e)}")
        except httpx.ReadTimeout as e:
            logger = LoggingManager.get_logger(__name__)
            logger.error(f"Read timeout in passthrough: {str(e)}", stack_info=True)
            raise HTTPException(status_code=HTTP_ERROR, detail=f"Passthrough request timed out: {str(e)}")
        except httpx.WriteTimeout as e:
            logger = LoggingManager.get_logger(__name__)
            logger.error(f"Write timeout in passthrough: {str(e)}", stack_info=True)
            raise HTTPException(status_code=HTTP_ERROR, detail=f"Passthrough request timed out: {str(e)}")
        except httpx.TimeoutException as e:
            logger = LoggingManager.get_logger(__name__)
            logger.error(f"General timeout in passthrough: {str(e)}", stack_info=True)
            raise HTTPException(status_code=HTTP_ERROR, detail=f"Passthrough request timed out: {str(e)}")
        except Exception as e:
            logger = LoggingManager.get_logger(__name__)
            logger.error(f"Error in generic passthrough: {str(e)}", stack_info=True)
            raise HTTPException(status_code=HTTP_ERROR, detail="Passthrough request failed")

    @staticmethod
    def _parse_request_body(request: Request, path: str) -> tuple:
        """Parse request body and determine if streaming is needed."""
        try:
            content_type = request.headers.get(CONTENT_TYPE_HEADER, "")
            is_json = CONTENT_TYPE_JSON in content_type.lower()

            body_bytes = asyncio.run(request.body())
            if not body_bytes:
                return {}, False

            if is_json:
                json_data = json.loads(body_bytes.decode('utf-8'))
                is_streaming = json_data.get('stream', False) or "stream" in path or "pull" in path
                return json_data, is_streaming
            else:
                return body_bytes, "stream" in path or "pull" in path

        except json.JSONDecodeError as je:
            logger = LoggingManager.get_logger(__name__)
            logger.error(f"Error decoding JSON: {str(je)}", stack_info=True)
            raise HTTPException(status_code=HTTP_BAD_REQUEST, detail="Invalid JSON in request body")
        except Exception:
            return b"", False

    @staticmethod
    def _handle_streaming_request(method: str, url: str, headers: dict, body) -> StreamingResponse:
        """Handle streaming requests."""
        def stream_response():
            # Create httpx client with timeout configuration for streaming
            timeout = httpx.Timeout(
                connect=OLLAMA_REQUEST_TIMEOUT,
                read=OLLAMA_REQUEST_TIMEOUT,
                write=OLLAMA_REQUEST_TIMEOUT,
                pool=OLLAMA_REQUEST_TIMEOUT
            )
            with httpx.stream(method, url, headers=headers, json=body if isinstance(body, dict) else None, content=body if not isinstance(body, dict) else None, timeout=timeout) as response:
                for chunk in response.iter_bytes():
                    yield chunk

        return StreamingResponse(stream_response(), media_type="application/x-ndjson", headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no"
        })

    @staticmethod
    def _handle_regular_request(method: str, url: str, headers: dict, body) -> Response:
        """Handle regular (non-streaming) requests."""
        # Create httpx client with timeout configuration
        timeout = httpx.Timeout(
            connect=OLLAMA_REQUEST_TIMEOUT,
            read=OLLAMA_REQUEST_TIMEOUT,
            write=OLLAMA_REQUEST_TIMEOUT,
            pool=OLLAMA_REQUEST_TIMEOUT
        )
        with httpx.Client(timeout=timeout) as client:
            if isinstance(body, dict):
                response = client.request(method, url, headers=headers, json=body)
            else:
                content = body if isinstance(body, bytes) else (body.encode() if isinstance(body, str) else body)
                response = client.request(method, url, headers=headers, content=content)

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )

