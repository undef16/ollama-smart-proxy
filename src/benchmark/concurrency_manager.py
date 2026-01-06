"""Manages concurrent request execution."""
import logging
import concurrent.futures
from typing import List, Tuple
import requests

from .models import BenchmarkConfig
from .request_executor import RequestExecutor


# Configure logging
logger = logging.getLogger(__name__)


class ConcurrencyManager:
    """Manages concurrent request execution."""
    
    def __init__(self, config: BenchmarkConfig, request_executor: RequestExecutor):
        self.config = config
        self.request_executor = request_executor

    def measure_latencies(self, session: requests.Session, url: str, concurrency: int, prompts: List[str], use_proxy: bool = False) -> List[tuple]:
        """
        Measure latencies with given concurrency using dataset prompts.

        Args:
            session: Requests session.
            url: API endpoint URL.
            concurrency: Number of concurrent workers.
            prompts: List of prompts to send.
            use_proxy: Whether to use proxy.

        Returns:
            List of tuples (latency, prompt_length, test_number).
        """
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(self.request_executor.send_request, session, url, prompts[i], use_proxy, test_number=i+1) for i in range(len(prompts))]
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error in request: {e}")
                    # Skip failed requests
                    continue

        return results