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
        self.logger.info(f"Configuration loaded. Plugins directory: {config.plugins_dir}, exists: {config.plugins_dir.exists()}")
        
        if not config.plugins_dir.exists():
            self.logger.warning(f"Plugins directory does not exist: {config.plugins_dir}")
            return

        plugin_dirs = list(config.plugins_dir.iterdir())
        self.logger.info(f"Found {len(plugin_dirs)} items in plugins directory: {[p.name for p in plugin_dirs]}")

        for plugin_dir in config.plugins_dir.iterdir():
            self.logger.debug(f"Processing plugin directory: {plugin_dir.name}, is_dir: {plugin_dir.is_dir()}")
            if not plugin_dir.is_dir():
                self.logger.debug(f"Skipping {plugin_dir.name} as it is not a directory")
                continue

            agent_file = plugin_dir / AGENT_FILE_NAME
            self.logger.debug(f"Checking for agent file: {agent_file}, exists: {agent_file.exists()}")
            if not agent_file.exists():
                self.logger.debug(f"No agent.py file found in {plugin_dir.name}, skipping")
                continue

            # Special logging for optimizer
            if plugin_dir.name == "optimizer":
                self.logger.info(f"DEBUG: Found optimizer plugin directory: {plugin_dir}")
                self.logger.info(f"DEBUG: Optimizer agent file exists: {agent_file.exists()}")

            self.logger.info(f"Loading modules from plugin directory: {plugin_dir.name}")
            # Load all .py files in the plugin directory as modules
            py_files = list(plugin_dir.glob("*.py"))
            self.logger.debug(f"Found {len(py_files)} Python files in {plugin_dir.name}: {[f.name for f in py_files]}")
            
            for py_file in py_files:
                if py_file.name == INIT_FILE_NAME:
                    self.logger.debug(f"Skipping __init__.py in {plugin_dir.name}")
                    continue
                    
                module_name = f"{PLUGINS_DIR_NAME}.{plugin_dir.name}.{py_file.stem}"
                self.logger.debug(f"Loading module: {module_name} from file: {py_file}")
                
                try:
                    spec = importlib.util.spec_from_file_location(module_name, py_file)
                    if spec is None or spec.loader is None:
                        self.logger.warning(f"Could not create spec for module {module_name}, spec: {spec}, loader: {getattr(spec, 'loader', 'N/A')}")
                        continue
                        
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[spec.name] = module
                    spec.loader.exec_module(module)
                    self.logger.debug(f"Successfully loaded module: {module_name}")
                except Exception as e:
                    self.logger.error(f"Failed to load module {module_name} from {py_file}: {str(e)}", stack_info=True)

            # The agent module is now loaded as plugins.{plugin_dir.name}.agent
            expected_module_name = f"{PLUGINS_DIR_NAME}.{plugin_dir.name}.{AGENT_FILE_NAME.split('.')[0]}"
            self.logger.debug(f"Looking for agent module: {expected_module_name}")
            agent_module = sys.modules.get(expected_module_name)
            if agent_module is None:
                self.logger.warning(f"Agent module {expected_module_name} was not found in sys.modules. Available modules: {[name for name in sys.modules.keys() if PLUGINS_DIR_NAME in name and plugin_dir.name in name]}")
                continue
            else:
                self.logger.info(f"Successfully found agent module: {expected_module_name}")

            # Find agent class in the agent module
            self.logger.debug(f"Searching for agent class in module: {expected_module_name}")
            agent_class = None
            attributes = dir(agent_module)
            self.logger.debug(f"Module {expected_module_name} contains {len(attributes)} attributes: {attributes[:10]}{'...' if len(attributes) > 10 else ''}")

            if plugin_dir.name == "optimizer":
                self.logger.info(f"DEBUG: Optimizer module attributes: {[attr for attr in attributes if not attr.startswith('_')]}")
            
            # Import BaseAgent directly from the same module where agent_module was loaded from
            # to ensure we're comparing against the same class definition
            from .base_agent import BaseAgent
            
            for attr_name in attributes:
                attr = getattr(agent_module, attr_name)
                if isinstance(attr, type):
                    # To handle the import path issue, we need to check if this class
                    # actually inherits from BaseAgent by checking its MRO (Method Resolution Order)
                    # We'll check both the direct subclass relationship and by name/module inspection
                    actual_base_agent = BaseAgent
                    is_subclass_result = issubclass(attr, actual_base_agent) if attr != actual_base_agent else False

                    # If the standard issubclass check failed, let's also check by looking at the MRO directly
                    if not is_subclass_result and attr != actual_base_agent:
                        # Check if BaseAgent appears in the MRO of this class
                        mro = attr.__mro__
                        for mro_class in mro:
                            if mro_class.__name__ == actual_base_agent.__name__ and mro_class.__module__.endswith(actual_base_agent.__module__):
                                is_subclass_result = True
                                break

                    if plugin_dir.name == "optimizer":
                        self.logger.info(f"DEBUG: Checking optimizer class {attr_name}: issubclass={is_subclass_result}, MRO={[cls.__name__ for cls in attr.__mro__]}")

                    self.logger.debug(f"Checking if {attr_name} ({attr}) is subclass of BaseAgent: {is_subclass_result}, BaseAgent from current context: {actual_base_agent}")
                    # Exclude the BaseAgent class itself, only allow actual agent implementations
                    if is_subclass_result and attr != actual_base_agent and attr.__name__ != 'BaseAgent':
                        self.logger.info(f"Found agent class {attr.__name__} in module {expected_module_name}")
                        if plugin_dir.name == "optimizer":
                            self.logger.info(f"DEBUG: Found optimizer agent class: {attr.__name__}")
                        agent_class = attr
                        break

            if agent_class is None:
                # Let's get more detailed info about classes in the module
                available_classes = []
                for name in attributes:
                    attr = getattr(agent_module, name)
                    if isinstance(attr, type):
                        # Check against the BaseAgent loaded in the current context
                        actual_base_agent = BaseAgent
                        is_subclass_result = issubclass(attr, actual_base_agent) if attr != actual_base_agent else False
                        
                        # If the standard check failed, try the MRO approach
                        if not is_subclass_result and attr != actual_base_agent:
                            mro = attr.__mro__
                            for mro_class in mro:
                                if mro_class.__name__ == actual_base_agent.__name__ and mro_class.__module__.endswith(actual_base_agent.__module__):
                                    is_subclass_result = True
                                    break
                        
                        # Exclude the BaseAgent class itself when reporting available classes
                        if attr != actual_base_agent and attr.__name__ != 'BaseAgent':
                            available_classes.append((name, is_subclass_result))
                        self.logger.debug(f"Class {name} ({attr}) subclass check: {is_subclass_result}, BaseAgent: {actual_base_agent}, same object: {attr is actual_base_agent}")
                
                self.logger.warning(f"No agent class found in module {expected_module_name}. Available classes: {available_classes}")
                self.logger.warning(f"BaseAgent in current context: {BaseAgent}, module: {BaseAgent.__module__}, id: {id(BaseAgent)}")
                # Check if there's a BaseAgent in the agent module that might be different
                if hasattr(agent_module, 'BaseAgent'):
                    module_base_agent = getattr(agent_module, 'BaseAgent')
                    self.logger.warning(f"BaseAgent in agent module: {module_base_agent}, module: {module_base_agent.__module__}, id: {id(module_base_agent)}, same as current: {module_base_agent is BaseAgent}")
                continue

            # Instantiate and register
            try:
                self.logger.info(f"Instantiating agent class: {agent_class.__name__} from plugin: {plugin_dir.name}")
                agent_instance = agent_class()
                self.logger.info(f"Successfully created agent instance with name: '{agent_instance.name}' from class: {agent_class.__name__}")
                self._agents[agent_instance.name] = agent_instance
            except Exception as e:
                self.logger.error(f"Failed to instantiate agent from class {agent_class.__name__} in plugin {plugin_dir.name}: {str(e)}", stack_info=True, exc_info=True)
                pass

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent instance by name."""
        self.logger.debug(f"Getting agent with name: {name}. Available agents: {list(self._agents.keys())}")
        return self._agents.get(name)

    @property
    def agents(self) -> Dict[str, BaseAgent]:
        """Get all loaded agents."""
        self.logger.debug(f"Returning agents: {list(self._agents.keys())}")
        return self._agents.copy()



