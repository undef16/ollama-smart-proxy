import importlib.util
import sys
from pathlib import Path
from typing import Dict, Optional

from shared.logging import LoggingManager

from .base_agent import BaseAgent
from .config import Config
from src.const import PLUGINS_DIR_NAME, AGENT_FILE_NAME, INIT_FILE_NAME


class PluginRegistry:
    """Registry for loading and managing agent plugins."""

    _instance: Optional['PluginRegistry'] = None

    def __new__(cls) -> 'PluginRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.logger = LoggingManager.get_logger(__name__)
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._agents: Dict[str, BaseAgent] = {}
            self._load_plugins()

    def _load_plugins(self) -> None:
        """Scan plugins directory and load agent classes."""
        config = Config()
        if not config.plugins_dir.exists():
            return

        for plugin_dir in config.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue

            agent_file = plugin_dir / AGENT_FILE_NAME
            if not agent_file.exists():
                continue

            # Load all .py files in the plugin directory as modules
            for py_file in plugin_dir.glob("*.py"):
                if py_file.name == INIT_FILE_NAME:
                    continue
                module_name = f"{PLUGINS_DIR_NAME}.{plugin_dir.name}.{py_file.stem}"
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)

            # The agent module is now loaded as plugins.{plugin_dir.name}.agent
            agent_module = sys.modules.get(f"{PLUGINS_DIR_NAME}.{plugin_dir.name}.{AGENT_FILE_NAME.split('.')[0]}")
            if agent_module is None:
                continue

            # Find agent class in the agent module
            agent_class = None
            for attr_name in dir(agent_module):
                attr = getattr(agent_module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseAgent)
                    and attr != BaseAgent
                ):
                    agent_class = attr
                    break

            if agent_class is None:
                continue

            # Instantiate and register
            try:
                agent_instance = agent_class()
                self._agents[agent_instance.name] = agent_instance
            except Exception as e:
                self.logger.error(f"Fail load agent {e}", stack_info=True)
                pass

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent instance by name."""
        return self._agents.get(name)

    @property
    def agents(self) -> Dict[str, BaseAgent]:
        """Get all loaded agents."""
        return self._agents.copy()



