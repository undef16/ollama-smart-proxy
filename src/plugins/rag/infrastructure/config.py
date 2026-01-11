"""Configuration management for the RAG plugin.

This module provides the ConfigurationManager class which implements the singleton
pattern for managing RAG configuration settings.
"""

import json
import logging
import os
from typing import Optional, Dict

from pydantic import BaseModel, Field, ValidationError

from .logging import ConfigurationError

logger = logging.getLogger(__name__)


class RAGConfig(BaseModel):
    """Configuration model for RAG plugin settings."""
    lightrag_host: str = Field(default="http://localhost:9621", description="LightRAG REST API host URL")
    lightrag_api_key: str = Field(default="", description="LightRAG API key for authentication")
    neo4j_uri: str = Field(..., description="Neo4j connection URI")
    postgres_uri: str = Field(..., description="PostgreSQL connection URI")
    searxng_host: str = Field(..., description="SearxNG host URL")
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")
    rag_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="RAG relevance threshold")
    max_documents: int = Field(default=5, ge=1, description="Maximum number of documents to retrieve")
    timeout: int = Field(default=30, ge=1, description="Timeout in seconds")
    cache_ttl: int = Field(default=3600, ge=1, description="Cache TTL in seconds")
    cache_size: int = Field(default=1000, ge=1, description="Cache size limit")
    embedding_model: str = Field(default="nomic-embed-text:latest", description="Embedding model name")
    llm_model: str = Field(default="qwen2.5-coder:1.5b", description="LLM model name")
    working_dir: str = Field(default="./rag_data", description="Working directory for RAG data")
    kv_storage: str = Field(default="RedisKVStorage", description="KV storage type")
    vector_storage: str = Field(default="PGVectorStorage", description="Vector storage type")
    graph_storage: str = Field(default="Neo4JStorage", description="Graph storage type")
    doc_status_storage: str = Field(default="PGDocStatusStorage", description="Document status storage type")
    circuit_breaker_failure_threshold: int = Field(default=5, description="Circuit breaker failure threshold")
    circuit_breaker_recovery_timeout: float = Field(default=60.0, description="Circuit breaker recovery timeout in seconds")
    circuit_breaker_success_threshold: int = Field(default=3, description="Circuit breaker success threshold")
    default_relevance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Default relevance score")
    max_query_length: int = Field(default=500, description="Maximum query length in characters")
    system_context: str = Field(default="You have access to the following relevant information:\n\n{context}\n\nBased on the above information, please assist with the user's request: {query}", description="System context template for RAG")
    relevance_evaluation_prompt_template: str = Field(
        default="Please evaluate the relevance of the following documents to the query: '{query}'\nRate each document on a scale from 0.0 to 1.0, where 1.0 is highly relevant and 0.0 is not relevant at all.\n\nDocuments:\n{documents}\n\nProvide your response as a JSON object with document scores:\n{{\"doc_1\": score1, \"doc_2\": score2, ...}}\nWhere each key corresponds to the document number.",
        description="Template for evaluating document relevance"
    )
    query_transformation_prompt_template: str = Field(
        default="Given the user query: '{query}', please generate a more specific and effective search query that would yield better results from a web search engine. The transformed query should focus on key terms and concepts that would help find relevant information.",
        description="Template for transforming queries for web search"
    )
    searxng_safesearch: int = Field(default=1, ge=0, le=2, description="SearxNG safe search level (0=none, 1=moderate, 2=strict)")

    def get_storage_config(self) -> Dict[str, str]:
        """Get storage configuration as a dictionary for LightRAG initialization."""
        return {
            "kv_storage": self.kv_storage,
            "vector_storage": self.vector_storage,
            "graph_storage": self.graph_storage,
            "doc_status_storage": self.doc_status_storage,
        }

    def get_database_urls(self) -> Dict[str, str]:
        """Get database connection URLs."""
        return {
            "neo4j_uri": self.neo4j_uri,
            "postgres_uri": self.postgres_uri,
        }


class ConfigurationManager:
    """Singleton manager for RAG configuration."""

    _instance: Optional['ConfigurationManager'] = None
    _config: Optional[RAGConfig] = None
    _static_config: Optional[RAGConfig] = None

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
    def config(self) -> Optional[RAGConfig]:
        """Get the current configuration."""
        return self._config

    def load(self, config_path: Optional[str] = None) -> RAGConfig:
        """Load configuration from a JSON file.

        Args:
            config_path: Optional custom path to config file.

        Returns:
            The loaded RAGConfig instance.

        Raises:
            ConfigurationError: If configuration file is not found,
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
            raise ConfigurationError(error_msg)

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in configuration file {config_path}: {e}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

        try:
            self._config = RAGConfig(**data)
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

    def get(self) -> RAGConfig:
        """Get the current configuration.

        Raises:
            ConfigurationError: If configuration is not loaded.
        """
        if self._config is None:
            error_msg = "Configuration not loaded. Call load() first."
            logger.error(error_msg)
            raise ConfigurationError(error_msg)
        return self._config

    def reload(self, config_path: Optional[str] = None) -> RAGConfig:
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

    def get_storage_config(self) -> Dict[str, str]:
        """Get storage configuration from loaded config."""
        return self.get().get_storage_config()

    def get_database_urls(self) -> Dict[str, str]:
        """Get database connection URLs from loaded config."""
        return self.get().get_database_urls()

    @staticmethod
    def get_config() -> RAGConfig:
        """Get the RAG configuration.

        This method provides backward compatibility with existing code.

        Returns:
            The current RAGConfig instance.

        Raises:
            ConfigurationError: If configuration cannot be loaded.
        """
        if ConfigurationManager._static_config is not None:
            return ConfigurationManager._static_config

        manager = ConfigurationManager.get_instance()
        ConfigurationManager._static_config = manager.load()
        return ConfigurationManager._static_config


