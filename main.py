"""Main entry point for the Ollama Smart Proxy."""

from fastapi import FastAPI

from src.shared.config import Config
from src.shared.logging import LoggingManager
from src.shared.plugin_registry import PluginRegistry
from src.shared.ollama_client import OllamaClient
from src.slices.chat.chat_router import ChatRouter
from src.slices.health.health_router import HealthRouter
from src.slices.passthrough.passthrough_router import PassthroughRouter
from src.slices.plugins.plugins_router import PluginsRouter

class OllamaSmartProxyApp:
    """Main application class for the Ollama Smart Proxy."""

    def __init__(self):
        # Setup logging
        LoggingManager.setup_logging()

        # Initialize plugin registry
        self.plugin_registry = PluginRegistry()

        # Initialize Ollama client
        self.ollama_client = OllamaClient()

        # Initialize routers
        self.chat_router = ChatRouter.get_router(self.plugin_registry, self.ollama_client)
        self.health_router = HealthRouter.get_router(self.ollama_client)
        self.passthrough_router = PassthroughRouter.get_router(self.ollama_client)
        self.plugins_router = PluginsRouter.get_router(self.plugin_registry)

        # Create FastAPI app
        self.app = FastAPI(
            title="Ollama Smart Proxy",
            description="A lightweight proxy server for Ollama that exposes OpenAI-compatible APIs",
            version="0.1.0",
        )

        # Mount slices
        self.app.include_router(self.chat_router)
        self.app.include_router(self.health_router)
        self.app.include_router(self.plugins_router)
        self.app.include_router(self.passthrough_router)


# Create application instance
app_instance = OllamaSmartProxyApp()
app = app_instance.app


if __name__ == "__main__":
    import uvicorn

    server_config = Config()
    uvicorn.run(app, host=server_config.server_host, port=server_config.server_port)