"""Main entry point for the Ollama Smart Proxy."""

from fastapi import FastAPI

from src.shared.config import Config
from src.shared.logging import LoggingManager
from src.shared.plugin_registry import PluginRegistry
from src.slices.chat.chat_router import ChatRouter
from src.slices.generate.generate_router import GenerateRouter
from src.slices.health.health_router import HealthRouter
from src.slices.passthrough.passthrough_router import PassthroughRouter
from src.slices.plugins.plugins_router import PluginsRouter
from src.const import APP_TITLE, APP_DESCRIPTION, APP_VERSION

class OllamaSmartProxyApp:
    """Main application class for the Ollama Smart Proxy."""

    def __init__(self):
        # Setup logging
        LoggingManager.setup_logging()

        # Initialize plugin registry
        self.plugin_registry = PluginRegistry()

        # Initialize routers
        self.chat_router = ChatRouter.get_router(self.plugin_registry)
        self.generate_router = GenerateRouter.get_router(self.plugin_registry)
        self.health_router = HealthRouter.get_router()
        self.passthrough_router = PassthroughRouter.get_router()
        self.plugins_router = PluginsRouter.get_router(self.plugin_registry)

        # Create FastAPI app
        self.app = FastAPI(
            title=APP_TITLE,
            description=APP_DESCRIPTION,
            version=APP_VERSION,
        )

        # Mount slices
        self.app.include_router(self.chat_router)
        self.app.include_router(self.generate_router)
        self.app.include_router(self.health_router)
        self.app.include_router(self.plugins_router)
        self.app.include_router(self.passthrough_router)


# Create application instance
app_instance = OllamaSmartProxyApp()
app = app_instance.app


if __name__ == "__main__":
    import uvicorn
    
    # Enable debugging if in development
    import os
    debug_mode = os.getenv('DEBUG', '').lower() in ('1', 'true', 'yes')
    
    if debug_mode:
        import debugpy
        debugpy.listen(("0.0.0.0", 5678))
        print("Waiting for debugger to attach on port 5678...")
        debugpy.wait_for_client()
        
    server_config = Config()
    
    # Only use reload in non-Docker environments for development
    reload_option = debug_mode and not os.path.exists('/.dockerenv')
    
    uvicorn.run(
        app,
        host=server_config.server_host,
        port=server_config.server_port,
        reload=reload_option  # Only enable hot reloading when not in Docker and in debug mode
    )