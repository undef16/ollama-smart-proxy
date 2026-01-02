from fastapi import APIRouter
from typing import List, Dict, Any

from shared.logging import LoggingManager
from shared.plugin_registry import PluginRegistry
from src.const import PLUGIN_STATUS_LOADED


class PluginsRouter:
    """Router for plugins endpoints."""

    def __init__(self, registry):
        self.registry = registry
        self.router = APIRouter(prefix="/plugins", tags=["plugins"])
        self.logger = LoggingManager.get_logger(__name__)
        self.router.get("", response_model=List[Dict[str, Any]])(self.list_plugins)

    @classmethod
    def get_router(cls, registry) -> APIRouter:
        """Get the router instance."""
        return cls(registry).router

    async def list_plugins(self) -> List[Dict[str, Any]]:
        """List all loaded plugins with their status."""
        try:
            plugins = []
            for agent in self.registry.agents.values():
                plugins.append({
                    "name": agent.name,
                    "status": PLUGIN_STATUS_LOADED
                })
            self.logger.info(f"Listed {len(plugins)} loaded plugins")
            return plugins
        except Exception as e:
            self.logger.error(f"Error listing plugins: {str(e)}")
            return []
