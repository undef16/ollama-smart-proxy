"""Generic ConfigurationManager for plugin configuration management.

This module provides a generic ConfigurationManager class that can be used by any plugin
to manage configuration settings following the singleton pattern.
"""

import json
import logging
import os
from typing import List, Optional, Type, TypeVar, Generic

from pydantic import BaseModel, ValidationError

# Define a basic ConfigurationError exception class to avoid dependency on RAG plugin
class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""
    
    def __init__(self, message: str, config_key: Optional[str] = None,
                 suggestions: Optional[List[str]] = None, cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.config_key = config_key
        self.suggestions = suggestions or []
        self.cause = cause

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class ConfigurationManager(Generic[T]):
    """Generic singleton manager for plugin configuration."""

    _instance: Optional['ConfigurationManager'] = None
    _config: Optional[T] = None
    _static_config: Optional[T] = None
    _config_class: Optional[Type[T]] = None

    def __new__(cls, config_class: Optional[Type[T]] = None) -> 'ConfigurationManager':
        """Create a singleton instance of ConfigurationManager.
        
        Args:
            config_class: The Pydantic model class to use for configuration
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            if config_class:
                cls._config_class = config_class
        return cls._instance

    def __init__(self, config_class: Optional[Type[T]] = None) -> None:
        """Initialize the configuration manager.
        
        Args:
            config_class: The Pydantic model class to use for configuration
        """
        if not self._initialized:
            self._config = None
            self._initialized = True
            if config_class:
                self._config_class = config_class
            logger.debug("ConfigurationManager initialized")

    @classmethod
    def get_instance(cls, config_class: Optional[Type[T]] = None) -> 'ConfigurationManager':
        """Get the singleton instance of ConfigurationManager.
        
        Args:
            config_class: The Pydantic model class to use for configuration
        
        Returns:
            The singleton ConfigurationManager instance
        """
        if cls._instance is None:
            cls._instance = cls(config_class)
        elif config_class and cls._config_class != config_class:
            # Allow reinitialization with different config class if needed
            cls._instance._config_class = config_class
            cls._instance._config = None
        return cls._instance

    @property
    def config(self) -> Optional[T]:
        """Get the current configuration.
        
        Returns:
            The current configuration instance
        """
        return self._config

    def load(self, config_path: Optional[str] = None, **kwargs) -> T:
        """Load configuration from a JSON file.
        
        Args:
            config_path: Optional custom path to config file
            **kwargs: Additional arguments to pass to the config class constructor

        Returns:
            The loaded configuration instance

        Raises:
            ConfigurationError: If configuration file is not found,
                               has invalid JSON, or fails validation.
        """
        if self._config is not None:
            logger.debug("Configuration already loaded, returning cached config")
            return self._config

        if config_path is None:
            # Default to config.json in the same directory as the calling module
            # This will be overridden by specific implementations
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')

        logger.info(f"Loading configuration from: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug("Configuration file loaded successfully")

        except FileNotFoundError as e:
            error_msg = f"Configuration file not found at {config_path}"
            logger.error(f"{error_msg}: {e}")
            raise ConfigurationError(error_msg)

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in configuration file {config_path}: {e}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

        try:
            if self._config_class:
                # Use from_env_and_json if available, otherwise use constructor
                if hasattr(self._config_class, 'from_env_and_json'):
                    self._config = self._config_class.from_env_and_json(data)
                else:
                    self._config = self._config_class(**data, **kwargs)
            else:
                raise ConfigurationError("Config class not set. Call get_instance() with config_class parameter.")
            logger.info("Configuration validated successfully")

        except ValidationError as e:
            error_msg = f"Configuration validation error: {e}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

        return self._config

    def validate(self) -> bool:
        """Validate the current configuration.
        
        Returns:
            True if configuration is valid.

        Raises:
            ConfigurationError: If configuration is not loaded or invalid.
        """
        if self._config is None:
            error_msg = "Configuration not loaded. Call load() first."
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

        self._config.model_validate(self._config.model_dump())
        logger.debug("Configuration validation passed")
        return True

    def get(self) -> T:
        """Get the current configuration.
        
        Returns:
            The current configuration instance.

        Raises:
            ConfigurationError: If configuration is not loaded.
        """
        if self._config is None:
            error_msg = "Configuration not loaded. Call load() first."
            logger.error(error_msg)
            raise ConfigurationError(error_msg)
        return self._config

    def reload(self, config_path: Optional[str] = None, **kwargs) -> T:
        """Reload configuration from file.
        
        Args:
            config_path: Optional custom path to config file
            **kwargs: Additional arguments to pass to the config class constructor

        Returns:
            The reloaded configuration instance
        """
        self._config = None
        logger.info("Configuration reload requested")
        return self.load(config_path, **kwargs)

    def reset(self) -> None:
        """Reset the configuration manager, clearing cached configuration."""
        self._config = None
        logger.info("Configuration manager reset")

    def is_loaded(self) -> bool:
        """Check if configuration has been loaded.
        
        Returns:
            True if configuration has been loaded, False otherwise
        """
        return self._config is not None

    @staticmethod
    def get_config(config_class: Type[T], config_path: Optional[str] = None, **kwargs) -> T:
        """Get the configuration using the generic ConfigurationManager.
        
        This method provides a convenient way to get configuration without
        explicitly managing the singleton instance.

        Args:
            config_class: The Pydantic model class to use for configuration
            config_path: Optional custom path to config file
            **kwargs: Additional arguments to pass to the config class constructor

        Returns:
            The current configuration instance.

        Raises:
            ConfigurationError: If configuration cannot be loaded.
        """
        if ConfigurationManager._static_config is not None:
            return ConfigurationManager._static_config

        manager = ConfigurationManager.get_instance(config_class)
        ConfigurationManager._static_config = manager.load(config_path, **kwargs)
        return ConfigurationManager._static_config