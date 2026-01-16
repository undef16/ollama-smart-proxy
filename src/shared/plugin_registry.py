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
            self.logger.info("Starting plugin registry initialization...")
            self._load_plugins()
            self.logger.info(f"Plugin registry initialization completed. Loaded agents: {list(self._agents.keys())}")

    def _load_plugins(self) -> None:
        """Scan plugins directory and load agent classes."""
        self.logger.info("Starting plugin loading process...")

        config = Config()
        plugins_dir = config.plugins_dir

        if not plugins_dir.exists():
            self.logger.warning(f"Plugins directory does not exist: {plugins_dir}")
            return

        self.logger.info(f"Scanning plugins directory: {plugins_dir}")
        plugin_dirs = [d for d in plugins_dir.iterdir() if d.is_dir()]
        self.logger.info(f"Found {len(plugin_dirs)} plugin directories")

        for plugin_dir in plugin_dirs:
            try:
                self._load_single_plugin(plugin_dir)
            except Exception as e:
                self.logger.error(f"Failed to load plugin from {plugin_dir.name}: {e}", exc_info=True)
                continue

    def _load_single_plugin(self, plugin_dir: Path) -> None:
        """Load a single plugin from the given directory."""
        plugin_name = plugin_dir.name
        self.logger.info(f"Loading plugin: {plugin_name}")

        # Validate plugin structure
        agent_file = plugin_dir / AGENT_FILE_NAME
        if not agent_file.exists():
            self.logger.debug(f"No {AGENT_FILE_NAME} found in {plugin_name}, skipping")
            return

        # Load the agent module
        module_name = f"{PLUGINS_DIR_NAME}.{plugin_name}.agent"
        try:
            agent_module = self._load_module(module_name, agent_file)
        except Exception as e:
            self.logger.error(f"Failed to load agent module for {plugin_name}: {e}")
            return

        # Find and validate agent class
        try:
            agent_class = self._find_agent_class(agent_module, plugin_name)
        except Exception as e:
            self.logger.error(f"Failed to find agent class in {plugin_name}: {e}")
            return

        # Instantiate and register agent
        try:
            self._instantiate_and_register_agent(agent_class, plugin_name)
        except Exception as e:
            self.logger.error(f"Failed to instantiate agent for {plugin_name}: {e}")

    def _load_module(self, module_name: str, file_path: Path) -> object:
        """Load a Python module from file."""
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Could not create module spec for {module_name}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        self.logger.debug(f"Successfully loaded module: {module_name}")
        return module

    def _find_agent_class(self, agent_module: object, plugin_name: str) -> type:
        """Find the agent class in the loaded module."""
        from .base_agent import BaseAgent

        # Get all classes from the module
        classes = [
            obj for name, obj in vars(agent_module).items()
            if isinstance(obj, type) and
               obj != BaseAgent and
               name != 'BaseAgent' and
               self._is_base_agent_subclass(obj, BaseAgent)
        ]

        if not classes:
            available_classes = [
                (name, self._is_base_agent_subclass(obj, BaseAgent))
                for name, obj in vars(agent_module).items()
                if isinstance(obj, type) and obj != BaseAgent
            ]
            raise ValueError(f"No valid agent class found. Available classes: {available_classes}")

        if len(classes) > 1:
            self.logger.warning(f"Multiple agent classes found in {plugin_name}, using first: {[cls.__name__ for cls in classes]}")

        agent_class = classes[0]
        self.logger.info(f"Found agent class: {agent_class.__name__} in plugin: {plugin_name}")
        return agent_class

    def _is_base_agent_subclass(self, cls: type, base_agent: type) -> bool:
        """Check if a class is a subclass of BaseAgent, handling import path issues."""
        try:
            return issubclass(cls, base_agent)
        except TypeError:
            # Handle cases where issubclass fails due to import path differences
            # Check MRO for BaseAgent by name and module
            for mro_class in cls.__mro__:
                if (mro_class.__name__ == base_agent.__name__ and
                    mro_class.__module__.endswith(base_agent.__module__.split('.')[-1])):
                    return True
            return False

    def _instantiate_and_register_agent(self, agent_class: type, plugin_name: str) -> None:
        """Instantiate an agent class and register it."""
        agent_instance = agent_class()
        agent_name = agent_instance.name

        if agent_name in self._agents:
            raise ValueError(f"Agent with name '{agent_name}' already exists")

        self._agents[agent_name] = agent_instance
        self.logger.info(f"Successfully registered agent: {agent_name} from plugin: {plugin_name}")

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent instance by name."""
        self.logger.debug(f"Getting agent with name: {name}. Available agents: {list(self._agents.keys())}")
        return self._agents.get(name)

    @property
    def agents(self) -> Dict[str, BaseAgent]:
        """Get all loaded agents."""
        self.logger.debug(f"Returning agents: {list(self._agents.keys())}")
        return self._agents.copy()



