from fastapi import APIRouter, Request

from shared.logging import LoggingManager
from shared.httpx_util import HTTPX_Util


class PassthroughRouter:
    """Router for passthrough endpoints."""

    def __init__(self):
        self.router = APIRouter(tags=["passthrough"])
        self.logger = LoggingManager.get_logger(__name__)
        self.router.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])(self.generic_passthrough)

    @classmethod
    def get_router(cls) -> APIRouter:
        """Get the router instance."""
        return cls().router

    def generic_passthrough(self, request: Request, path: str):
       """Generic passthrough for any Ollama API request."""
       # Delegate to the generic utility function
       return HTTPX_Util.generic_passthrough(request, path)
