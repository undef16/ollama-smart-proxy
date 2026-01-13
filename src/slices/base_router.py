"""Base class for routers in the Ollama Smart Proxy."""

from abc import ABC, abstractmethod
from fastapi import APIRouter


class BaseRouter(ABC):
    """Base class for API routers."""

    chain_class = None
    tag = None

    def __init__(self, registry):
        self.registry = registry
        self.chain = self.chain_class(registry)
        self.router = APIRouter(tags=[self.tag])
        self.add_routes()

    @abstractmethod
    def add_routes(self):
        """Add routes to the router."""
        pass

    @classmethod
    def get_router(cls, registry) -> APIRouter:
        """Get the router instance."""
        return cls(registry).router