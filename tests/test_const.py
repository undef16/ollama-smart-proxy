"""Constants used across all test files."""

# Common test values
TEST_MODEL = "test-model"
TEST_PROMPT = "test prompt"
TEST_RESPONSE = "test response"
TEST_HOST = "localhost"
TEST_PORT = 11434
TEST_HOST_OVERRIDE = "test-host"
TEST_PORT_OVERRIDE = 9999
TEST_PORT_OVERRIDE_2 = 8080
TEST_AGENT_NAME = "test_agent"
TEST_AGENT = "test"
EXAMPLE_AGENT = "example"

# Mock return values
MOCK_CHAT_RESPONSE = {"response": "test"}
MOCK_GENERATE_RESPONSE = {"response": "generated"}
MOCK_LIST_RESPONSE = {"models": []}
MOCK_PULL_RESPONSE = {"status": "success"}
MOCK_SHOW_RESPONSE = {"info": "model info"}
MOCK_DELETE_RESPONSE = {"status": "deleted"}
MOCK_EMBEDDINGS_RESPONSE = {"embeddings": [0.1, 0.2]}
MOCK_PROCESSED_RESPONSE = {"response": "processed response"}

# Token counts and performance values
PROMPT_EVAL_COUNT = 100
EVAL_COUNT = 50
INVALID_TOKEN_COUNT = -1

# Optimizer metadata values
TEMPLATE_ID = 1
CONFIDENCE_SCORE = 0.9
DISTANCE_VALUE = 3
REASONING_TEXT = "Test reasoning"

# Configuration paths
PLUGINS_DIR_PATH = "src/plugins"
TEST_PLUGINS_DIR_PATH = "/test/plugins"

# HTTP and API constants
HTTP_SUCCESS = 200
HTTP_ERROR = 500
STREAM_VALUE = True
NO_STREAM_VALUE = False

# Boolean values
TRUE_VALUE = True
FALSE_VALUE = False

# Numeric values
ZERO_VALUE = 0
ONE_VALUE = 1
DEFAULT_CTX_VALUE = 1024

# String values
EMPTY_STRING = ""
WHITESPACE_STRING = "   "
DEFAULT_STRING = "test"

# None values
NONE_VALUE = None