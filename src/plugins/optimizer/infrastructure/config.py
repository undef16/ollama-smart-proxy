"""Configuration management for the Optimizer plugin.

This module provides the ConfigurationManager class which implements the singleton
pattern for managing Optimizer configuration settings.
"""

import json
import logging
import os
from typing import Optional, Dict

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class OptimizerConfig(BaseModel):
    """Configuration model for Optimizer plugin settings."""
    database_type: str = Field(default="sqlite", description="Database type (sqlite or postgres)")
    database_path: str = Field(default="./src/plugins/optimizer/data/optimizer_stats.db", description="SQLite database path")
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_user: str = Field(default="ollama_proxy", description="PostgreSQL user")
    postgres_password: str = Field(default="pass", description="PostgreSQL password")
    postgres_db: str = Field(default="optimizer", description="PostgreSQL database name")
    safety_margin: float = Field(default=1.2, ge=1.0, description="Safety margin for context window calculation")
    template_cache_max_size: int = Field(default=512, ge=1, description="Maximum size of template cache")
    template_cache_ttl: int = Field(default=1800, ge=1, description="TTL for template cache in seconds")
    fingerprint_cache_max_size: int = Field(default=1000, ge=1, description="Maximum size of fingerprint cache")
    fingerprint_cache_ttl: int = Field(default=3600, ge=1, description="TTL for fingerprint cache in seconds")
    tokenizer_cache_max_size: int = Field(default=500, ge=1, description="Maximum size of tokenizer cache")
    tokenizer_cache_ttl: int = Field(default=3600, ge=1, description="TTL for tokenizer cache in seconds")
    query_cache_max_size: int = Field(default=200, ge=1, description="Maximum size of query cache")
    query_cache_ttl: int = Field(default=1800, ge=1, description="TTL for query cache in seconds")

    @property
    def postgres_connection_string(self) -> str:
        """Generate PostgreSQL connection string from individual components."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @classmethod
    def from_env_and_json(cls, json_data: Dict) -> 'OptimizerConfig':
        """Create OptimizerConfig from JSON data with environment variable overrides.

        Environment variables will override JSON values if they exist.
        Supported environment variables:
        - OPTIMIZER_DATABASE_TYPE
        - OPTIMIZER_DATABASE_PATH
        - OPTIMIZER_POSTGRES_CONNECTION_STRING
        - OPTIMIZER_SAFETY_MARGIN
        - OPTIMIZER_TEMPLATE_CACHE_MAX_SIZE
        - OPTIMIZER_TEMPLATE_CACHE_TTL
        """
        # Start with JSON data
        config_data = json_data.copy()

        # Override with environment variables if they exist
        env_mappings = {
            'OPTIMIZER_DATABASE_TYPE': 'database_type',
            'OPTIMIZER_DATABASE_PATH': 'database_path',
            'OPTIMIZER_POSTGRES_HOST': 'postgres_host',
            'OPTIMIZER_POSTGRES_PORT': 'postgres_port',
            'OPTIMIZER_POSTGRES_USER': 'postgres_user',
            'OPTIMIZER_POSTGRES_PASSWORD': 'postgres_password',
            'OPTIMIZER_POSTGRES_DB': 'postgres_db',
            'OPTIMIZER_SAFETY_MARGIN': 'safety_margin',
            'OPTIMIZER_TEMPLATE_CACHE_MAX_SIZE': 'template_cache_max_size',
            'OPTIMIZER_TEMPLATE_CACHE_TTL': 'template_cache_ttl',
            'OPTIMIZER_FINGERPRINT_CACHE_MAX_SIZE': 'fingerprint_cache_max_size',
            'OPTIMIZER_FINGERPRINT_CACHE_TTL': 'fingerprint_cache_ttl',
            'OPTIMIZER_TOKENIZER_CACHE_MAX_SIZE': 'tokenizer_cache_max_size',
            'OPTIMIZER_TOKENIZER_CACHE_TTL': 'tokenizer_cache_ttl',
            'OPTIMIZER_QUERY_CACHE_MAX_SIZE': 'query_cache_max_size',
            'OPTIMIZER_QUERY_CACHE_TTL': 'query_cache_ttl',
        }

        for env_var, config_key in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Convert string values to appropriate types
                if config_key in ['safety_margin']:
                    try:
                        config_data[config_key] = float(env_value)
                    except ValueError:
                        logger.warning(f"Invalid float value for {env_var}: {env_value}")
                elif config_key in ['template_cache_max_size', 'template_cache_ttl', 'fingerprint_cache_max_size',
                                   'fingerprint_cache_ttl', 'tokenizer_cache_max_size', 'tokenizer_cache_ttl',
                                   'query_cache_max_size', 'query_cache_ttl', 'postgres_port']:
                    try:
                        config_data[config_key] = int(env_value)
                    except ValueError:
                        logger.warning(f"Invalid integer value for {env_var}: {env_value}")
                else:
                    config_data[config_key] = env_value
                logger.debug(f"Overriding {config_key} with environment variable {env_var}")

        return cls(**config_data)


class ConfigurationManager:
    """Singleton manager for Optimizer configuration."""

    _instance: Optional['ConfigurationManager'] = None
    _config: Optional[OptimizerConfig] = None
    _static_config: Optional[OptimizerConfig] = None

    def __new__(cls) -> 'ConfigurationManager':
        """Create a singleton instance of ConfigurationManager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the configuration manager."""
        if not self._initialized:
            self._config = None
            self._initialized = True
            logger.debug("ConfigurationManager initialized")

    @classmethod
    def get_instance(cls) -> 'ConfigurationManager':
        """Get the singleton instance of ConfigurationManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def config(self) -> Optional[OptimizerConfig]:
        """Get the current configuration."""
        return self._config

    def load(self, config_path: Optional[str] = None) -> OptimizerConfig:
        """Load configuration from a JSON file.

        Args:
            config_path: Optional custom path to config file.

        Returns:
            The loaded OptimizerConfig instance.

        Raises:
            ValueError: If configuration file is not found,
                       has invalid JSON, or fails validation.
        """
        if self._config is not None:
            logger.debug("Configuration already loaded, returning cached config")
            return self._config

        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')

        logger.info(f"Loading configuration from: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug("Configuration file loaded successfully")

        except FileNotFoundError as e:
            error_msg = f"Configuration file not found at {config_path}"
            logger.error(f"{error_msg}: {e}")
            raise ValueError(error_msg)

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in configuration file {config_path}: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            self._config = OptimizerConfig.from_env_and_json(data)
            logger.info("Configuration validated successfully")

        except ValidationError as e:
            error_msg = f"Configuration validation error: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        return self._config

    def validate(self) -> bool:
        """Validate the current configuration.

        Returns:
            True if configuration is valid.

        Raises:
            ValueError: If configuration is not loaded or invalid.
        """
        if self._config is None:
            error_msg = "Configuration not loaded. Call load() first."
            logger.error(error_msg)
            raise ValueError(error_msg)

        self._config.model_validate(self._config.model_dump())
        logger.debug("Configuration validation passed")
        return True

    def get(self) -> OptimizerConfig:
        """Get the current configuration.

        Raises:
            ValueError: If configuration is not loaded.
        """
        if self._config is None:
            error_msg = "Configuration not loaded. Call load() first."
            logger.error(error_msg)
            raise ValueError(error_msg)
        return self._config

    def reload(self, config_path: Optional[str] = None) -> OptimizerConfig:
        """Reload configuration from file."""
        self._config = None
        logger.info("Configuration reload requested")
        return self.load(config_path)

    def reset(self) -> None:
        """Reset the configuration manager, clearing cached configuration."""
        self._config = None
        logger.info("Configuration manager reset")

    def is_loaded(self) -> bool:
        """Check if configuration has been loaded."""
        return self._config is not None

    @staticmethod
    def get_config() -> OptimizerConfig:
        """Get the Optimizer configuration.

        This method provides backward compatibility with existing code.

        Returns:
            The current OptimizerConfig instance.

        Raises:
            ValueError: If configuration cannot be loaded.
        """
        if ConfigurationManager._static_config is not None:
            return ConfigurationManager._static_config

        manager = ConfigurationManager.get_instance()
        ConfigurationManager._static_config = manager.load()
        return ConfigurationManager._static_config