from fastapi import APIRouter
from typing import Dict, Any

from shared.logging import LoggingManager


class HealthRouter:
    """Router for health endpoints."""

    def __init__(self, ollama_client):
        self.ollama_client = ollama_client
        self.router = APIRouter(prefix="/health", tags=["health"])
        self.logger = LoggingManager.get_logger(__name__)
        self.router.get("", response_model=Dict[str, Any])(self.health_check)

    @classmethod
    def get_router(cls, ollama_client) -> APIRouter:
        """Get the router instance."""
        return cls(ollama_client).router

    async def health_check(self) -> Dict[str, Any]:
        """Check health of proxy and upstream Ollama server."""
        proxy_status = "Ok"
        upstream_status = "Ok"

        try:
            self.logger.debug("Checking upstream Ollama health")
            # Ping upstream by listing models
            await self.ollama_client.list()
            self.logger.debug("Upstream Ollama health check passed")
        except Exception as e:
            upstream_status = "error"
            self.logger.warning(f"Upstream Ollama health check failed: {str(e)}")

        status = "healthy" if upstream_status == "Ok" else "unhealthy"
        self.logger.info(f"Health check result: {status} (proxy: {proxy_status}, upstream: {upstream_status})")

        return {
            "status": status,
            "proxy": proxy_status,
            "upstream": upstream_status
        }
