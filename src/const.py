"""Constants for the Ollama Smart Proxy."""

# Default configuration values
DEFAULT_OLLAMA_HOST = "localhost"
DEFAULT_OLLAMA_PORT = 11434
DEFAULT_PLUGINS_DIR = "src/plugins"
DEFAULT_MODEL_CACHE_TTL = 300
DEFAULT_AGENT_COMMAND_PATTERN = r"/(\w+)"
DEFAULT_SERVER_HOST = "0.0.0.0"
DEFAULT_SERVER_PORT = 11555

# Logging configuration
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Library log levels
LIBRARY_LOG_LEVELS = {
    "uvicorn": "WARNING",
    "uvicorn.access": "WARNING",
    "fastapi": "WARNING",
    "httpx": "WARNING"
}

# HTTP status codes
HTTP_SUCCESS = 200
HTTP_BAD_REQUEST = 400
HTTP_ERROR = 500

# Default values for request processing
STREAM_VALUE = True
NO_STREAM_VALUE = False
TRUE_VALUE = True
FALSE_VALUE = False
ZERO_VALUE = 0
ONE_VALUE = 1
DEFAULT_CTX_VALUE = 1024
EMPTY_STRING = ""

# Cache configuration
DEFAULT_CACHE_TTL = 300

# Agent-related constants
DEFAULT_AGENT_NAME = "default"