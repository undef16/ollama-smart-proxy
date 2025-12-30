import importlib.util
import sys
from pathlib import Path
from typing import Dict, Optional

from .base_agent import BaseAgent
from .config import Config


class PluginRegistry:
    """Registry for loading and managing agent plugins."""

    _instance: Optional['PluginRegistry'] = None

    def __new__(cls) -> 'PluginRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
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

            agent_file = plugin_dir / "agent.py"
            if not agent_file.exists():
                continue

            # Load the module
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_dir.name}", agent_file
            )
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            # Find agent class
            agent_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
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
            except Exception:
                # Log error, but continue loading others
                pass

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent instance by name."""
        return self._agents.get(name)

    @property
    def agents(self) -> Dict[str, BaseAgent]:
        """Get all loaded agents."""
        return self._agents.copy()



