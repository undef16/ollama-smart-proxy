"""Shared test configuration and fixtures for all tests."""

import pytest
import os
from unittest.mock import MagicMock, AsyncMock, patch
from .test_const import (
    MOCK_CHAT_RESPONSE, MOCK_GENERATE_RESPONSE, MOCK_LIST_RESPONSE,
    MOCK_PULL_RESPONSE, MOCK_SHOW_RESPONSE, MOCK_DELETE_RESPONSE,
    MOCK_EMBEDDINGS_RESPONSE, TEST_MODEL, TEST_PROMPT, MOCK_PROCESSED_RESPONSE,
    TEST_HOST, TEST_PORT
)


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client fixture."""
    mock_client = MagicMock()
    mock_client.chat = AsyncMock(return_value=MOCK_CHAT_RESPONSE)
    mock_client.generate = AsyncMock(return_value=MOCK_GENERATE_RESPONSE)
    mock_client.list = AsyncMock(return_value=MOCK_LIST_RESPONSE)
    mock_client.pull = AsyncMock(return_value=MOCK_PULL_RESPONSE)
    mock_client.show = AsyncMock(return_value=MOCK_SHOW_RESPONSE)
    mock_client.delete = AsyncMock(return_value=MOCK_DELETE_RESPONSE)
    mock_client.embeddings = AsyncMock(return_value=MOCK_EMBEDDINGS_RESPONSE)
    return mock_client


@pytest.fixture
def mock_registry():
    """Mock plugin registry fixture."""
    return MagicMock()


@pytest.fixture
def mock_agent():
    """Mock agent fixture."""
    mock_agent = MagicMock()
    mock_agent.name = "test_agent"
    mock_agent.on_request = AsyncMock(return_value={"model": TEST_MODEL, "prompt": TEST_PROMPT})
    mock_agent.on_response = AsyncMock(return_value=MOCK_PROCESSED_RESPONSE)
    return mock_agent


@pytest.fixture
def mock_logging():
    """Mock logging module fixture."""
    with patch('src.shared.logging.logging') as mock_logging:
        yield mock_logging


@pytest.fixture
def mock_ollama():
    """Mock ollama module fixture."""
    with patch('src.shared.ollama_client.ollama') as mock_ollama:
        mock_client = MagicMock()
        mock_ollama.Client.return_value = mock_client
        yield mock_ollama


@pytest.fixture
def mock_settings():
    """Mock settings fixture."""
    with patch('src.shared.config.Config') as mock_settings_class:
        mock_settings = MagicMock()
        mock_settings.ollama_host = TEST_HOST
        mock_settings.ollama_port = TEST_PORT
        mock_settings.plugins_dir = MagicMock()
        mock_settings.plugins_dir.exists.return_value = True
        mock_settings.plugins_dir.iterdir.return_value = []
        mock_settings_class.return_value = mock_settings
        yield mock_settings


class MockOllamaClientBuilder:
    """Builder for creating mock Ollama clients with specific return values."""
    
    def __init__(self):
        self.mock_client = MagicMock()
        self.mock_client.chat = AsyncMock()
        self.mock_client.generate = AsyncMock()
        self.mock_client.list = AsyncMock()
        self.mock_client.pull = AsyncMock()
        self.mock_client.show = AsyncMock()
        self.mock_client.delete = AsyncMock()
        self.mock_client.embeddings = AsyncMock()
    
    def with_chat_response(self, response):
        self.mock_client.chat.return_value = response
        return self
    
    def with_generate_response(self, response):
        self.mock_client.generate.return_value = response
        return self
    
    def with_list_response(self, response):
        self.mock_client.list.return_value = response
        return self
    
    def with_pull_response(self, response):
        self.mock_client.pull.return_value = response
        return self
    
    def build(self):
        return self.mock_client


@pytest.fixture
def mock_ollama_client_builder():
    """Builder fixture for creating mock Ollama clients."""
    return MockOllamaClientBuilder()


def assert_called_once_with_kwargs(mock_obj, **expected_kwargs):
    """Helper to assert a mock was called once with specific keyword arguments."""
    assert mock_obj.call_count == 1
    actual_kwargs = mock_obj.call_args[1]  # Get the keyword arguments
    for key, expected_value in expected_kwargs.items():
        assert key in actual_kwargs, f"Expected keyword argument '{key}' not found in call"
        assert actual_kwargs[key] == expected_value, f"Expected {key}={expected_value}, got {actual_kwargs[key]}"


# PostgreSQL testcontainers fixture
_postgres_container = None
_postgres_container_used = False


def _get_postgres_connection_string():
    """Get PostgreSQL connection string from environment or testcontainers."""
    global _postgres_container, _postgres_container_used
    
    # First check if PostgreSQL is already available (local instance)
    env_conn_str = os.environ.get(
        "POSTGRES_CONNECTION_STRING",
        "postgresql://postgres:postgres@localhost:5432/optimizer"
    )
    
    # Try to use local PostgreSQL if available
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(env_conn_str)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return env_conn_str
    except Exception:
        pass
    
    # Try to use testcontainers if Docker is available
    try:
        from testcontainers.postgres import PostgresContainer
        if _postgres_container is None:
            _postgres_container = PostgresContainer("postgres:16-alpine")
            _postgres_container.start()
            _postgres_container_used = True
        return _postgres_container.get_connection_url()
    except Exception as e:
        # Docker not available or testcontainers failed
        return None


@pytest.fixture(scope="session")
def postgres_connection_string():
    """Session-scoped fixture that provides PostgreSQL connection string.
    
    Tries in order:
    1. Local PostgreSQL (via POSTGRES_CONNECTION_STRING env var)
    2. testcontainers (spins up a PostgreSQL container)
    3. Returns None if neither is available
    """
    global _postgres_container, _postgres_container_used
    
    conn_str = _get_postgres_connection_string()
    yield conn_str
    # Cleanup container after all tests (only if we started it)
    if _postgres_container_used and _postgres_container is not None:
        _postgres_container.stop()
        _postgres_container = None
        _postgres_container_used = False


@pytest.fixture
def postgres_repo(postgres_connection_string):
    """Create a PostgreSQL template repository for testing.
    
    Skips tests if PostgreSQL is not available (neither local nor via testcontainers).
    """
    if postgres_connection_string is None:
        pytest.skip("PostgreSQL not available (neither local instance nor Docker/testcontainers)")
    
    from src.plugins.optimizer.infrastructure.adapters.postgres_adapter import PostgreSQLTemplateRepository
    repo = PostgreSQLTemplateRepository(connection_string=postgres_connection_string)
    yield repo
    repo.close()
