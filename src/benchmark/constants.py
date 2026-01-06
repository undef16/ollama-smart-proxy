"""Constants for the benchmarking system."""
from typing import List


class BenchmarkConstants:
    """Centralized constants for benchmark configuration."""
    # model: str = "gemma3:1b"
    # model: str = "gemma3:4b"
    # model: str = "gemma3n:e2b"
    # model: str = "qwen2.5-coder:1.5b"
    # model: str = "gemma3:12b"
    # model: str = "gpt-oss:latest"
    DEFAULT_MODEL = "qwen2.5-coder:1.5b"
    CLEAR_MODEL = "gemma3:4b"
    DEFAULT_TIMEOUT = 300  # seconds
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_CONCURRENCIES = [1,2,3] #,2,3,4
    DEFAULT_REQUESTS = 5 # 2294
    PROXY_PREFIX = "/opt "
    CONTEXT_WINDOW = 32768
    SEED = 42
