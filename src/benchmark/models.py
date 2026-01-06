"""Data models for the benchmarking system."""
from dataclasses import dataclass
from typing import List


@dataclass
class BenchmarkConfig:
    """Configuration for the benchmark."""
    ollama_direct_url: str = "http://localhost:11434/api/chat"
    proxy_url: str = "http://localhost:11555/api/chat"


@dataclass
class LatencyResults:
    """Container for latency percentiles."""
    p50: float
    p90: float
    p95: float
