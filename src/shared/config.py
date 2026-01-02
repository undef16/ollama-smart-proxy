import json
import os
from pathlib import Path
from typing import Dict, Any

from pydantic import ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.const import (
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_PORT,
    DEFAULT_PLUGINS_DIR,
    DEFAULT_MODEL_CACHE_TTL,
    DEFAULT_AGENT_COMMAND_PATTERN,
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    LIBRARY_LOG_LEVELS,
    CONFIG_FILE_NAME
)


class Config(BaseSettings):
    """Global configuration settings for the Ollama Smart Proxy."""

    ollama_host: str = DEFAULT_OLLAMA_HOST
    ollama_port: int = DEFAULT_OLLAMA_PORT
    plugins_dir: Path = Path(DEFAULT_PLUGINS_DIR)
    model_cache_ttl: int = DEFAULT_MODEL_CACHE_TTL
    agent_command_pattern: str = DEFAULT_AGENT_COMMAND_PATTERN
    server_host: str = DEFAULT_SERVER_HOST
    server_port: int = DEFAULT_SERVER_PORT
    library_log_levels: Dict[str, str] = LIBRARY_LOG_LEVELS

    model_config = SettingsConfigDict(
        protected_namespaces=('settings_',),
        env_prefix='OLLAMA_PROXY_',
    )

    @classmethod
    def load_config_from_json(cls) -> Dict[str, Any]:
        """Load configuration from config.json file."""
        config_path = Path(CONFIG_FILE_NAME)
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Convert plugins_dir to Path if it's a string
                if "plugins_dir" in config:
                    config["plugins_dir"] = Path(config["plugins_dir"])
                return config
        return {}

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """
        Customise the sources for settings.

        Order of precedence (highest to lowest):
        1. Environment variables
        2. Init settings (kwargs passed to constructor)
        3. JSON config file
        4. Default values
        """
        def json_source():
            return cls.load_config_from_json()

        return (
            env_settings,
            init_settings,
            json_source,
        )