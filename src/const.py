"""Constants for the Ollama Smart Proxy."""

# Default configuration values
DEFAULT_OLLAMA_HOST = "localhost"
DEFAULT_OLLAMA_PORT = 11434
DEFAULT_PLUGINS_DIR = "src/plugins"
DEFAULT_DATABASE_TYPE = "sqlite"
CACHE_TTL = 300
DEFAULT_MODEL_CACHE_TTL = CACHE_TTL
DEFAULT_AGENT_COMMAND_PATTERN = r"^\s*/(\w+)\s*"
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
DEFAULT_CACHE_TTL = CACHE_TTL

# Agent-related constants
DEFAULT_AGENT_NAME = "default"

# Request/Response field names
MODEL_FIELD = "model"
MESSAGES_FIELD = "messages"
PROMPT_FIELD = "prompt"
STREAM_FIELD = "stream"
RESPONSE_FIELD = "response"
MESSAGE_FIELD = "message"
CONTENT_FIELD = "content"
ROLE_FIELD = "role"
AGENTS_FIELD = "agents"
DONE_FIELD = "done"
ERROR_FIELD = "error"

# Message roles
USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"
SYSTEM_ROLE = "system"

# Streaming constants
STREAMING_MEDIA_TYPE = "application/x-ndjson"
CACHE_CONTROL_NO_CACHE = "no-cache"

# Health check constants
HEALTH_STATUS_HEALTHY = "healthy"
HEALTH_STATUS_UNHEALTHY = "unhealthy"
HEALTH_STATUS_OK = "Ok"
HEALTH_STATUS_ERROR = "error"
HEALTH_PROXY_STATUS_OK = HEALTH_STATUS_OK
HEALTH_UPSTREAM_STATUS_OK = HEALTH_STATUS_OK
HEALTH_UPSTREAM_STATUS_ERROR = HEALTH_STATUS_ERROR

# Plugin constants
PLUGIN_STATUS_LOADED = "loaded"

# File and directory names
CONFIG_FILE_NAME = "config.json"
PLUGINS_DIR_NAME = "plugins"
AGENT_FILE_NAME = "agent.py"
INIT_FILE_NAME = "__init__.py"

# FastAPI app constants
APP_TITLE = "Ollama Smart Proxy"
APP_DESCRIPTION = "A lightweight proxy server for Ollama that exposes OpenAI-compatible APIs"
APP_VERSION = "0.1.0"


# HTTP headers
CONTENT_TYPE_HEADER = "content-type"
CONTENT_TYPE_JSON = "application/json"
HOST_HEADER = "host"

# Error messages and placeholders
NO_CONTENT_PLACEHOLDER = "NO CONTENT"
NO_RESPONSE_PLACEHOLDER = "NO RESPONSE"
UNKNOWN_ROLE = "unknown"

# Test and simulation constants (for main_sim.py)
DEFAULT_TEST_MODEL = "qwen2.5-coder:1.5b"
TEST_MODELS_LIST = ["qwen3:8b", "gemma3:4b"]
PROXY_HOST_URL = "http://localhost"
SERVER_START_TIMEOUT_SEC = 60
HTTP_TIMEOUT_SEC = 30
OLLAMA_REQUEST_TIMEOUT = 300  # Increased timeout for Ollama requests
MAX_RETRY_ATTEMPTS = 3
EXAMPLE_AGENT_SUFFIX_STR = " [processed by example agent]"

# Test prompts instruction
OPT_INSTRUCTION = "You are an expert in natural language processing and machine learning. Your primary task is to carefully analyze the provided text input for multiple key aspects. These include but are not limited to: overall sentiment analysis (positive, negative, neutral), extraction of named entities such as people, organizations, locations, dates, and other relevant items, identification of the main topics and subtopics discussed, detection of any potential biases or emotional tones, and summarization of the core message. After analysis, provide a comprehensive report in a well-structured JSON format with sections for each aspect. Ensure the report is objective, accurate, and detailed."

# Test prompts
TEST_PROMPT_SIMPLE = "Hello, world!"
TEST_PROMPT_WITH_AGENT = "/example Hello, world!"
TEST_PROMPT_OPT_POSITIVE = f"/opt {OPT_INSTRUCTION} Input text for analysis: The movie was fantastic and thrilling."
TEST_PROMPT_OPT_NEGATIVE = f"/opt {OPT_INSTRUCTION} Input text for analysis: The service was terrible and slow."
TEST_PROMPT_RAG = "/rag The date of the first Python release?"
