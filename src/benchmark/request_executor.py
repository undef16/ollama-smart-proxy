"""Handles individual request execution and timing."""
import time
import logging
from typing import Tuple
import requests

from .models import BenchmarkConfig
from .constants import BenchmarkConstants
from .exceptions import RequestError


# Configure logging
logger = logging.getLogger(__name__)


class RequestExecutor:
    """Handles individual request execution and timing."""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config

    def send_request(self, session: requests.Session, url: str, prompt: str, use_proxy: bool = False, model: str = None, test_number: int = None) -> tuple:
        """
        Send a single request to Ollama and measure latency.

        Args:
            session: Requests session with retries.
            url: API endpoint URL.
            prompt: The prompt to send.
            use_proxy: Whether to use proxy prefix.
            model: The model to use for the request. If None, uses DEFAULT_MODEL.
            test_number: The test number/index for tracking (optional).

        Returns:
            Tuple of (latency in seconds, prompt_length, test_number).

        Raises:
            RequestError: If request fails.
        """
        if use_proxy:
            prompt = BenchmarkConstants.PROXY_PREFIX + prompt  # Activate optimizer for proxy

        prompt_length = len(prompt)

        # Use the specified model or default to BenchmarkConstants.DEFAULT_MODEL
        model_to_use = model if model is not None else BenchmarkConstants.DEFAULT_MODEL

        payload = {
            "model": model_to_use,
            # "prompt": prompt,
            "messages": [
                {
                "role": "user",
                "content": f"{prompt}"
                }
            ],
            "stream": False,
            "options":{
                # "num_ctx": num_ctx,
                "num_ctx": BenchmarkConstants.CONTEXT_WINDOW,
                "seed": BenchmarkConstants.SEED,
                "keep_alive": 0,
                "stream" : False,
                "raw": False
            }
        }

        start_time = time.perf_counter()
        try:
            # print(f"Request: {payload}")
            response = session.post(url, json=payload, timeout=BenchmarkConstants.DEFAULT_TIMEOUT)
            response.raise_for_status()
            # Optionally validate response content
            # data = response.json()
            # print(f"Response: {data}")
            # if 'response' not in data:
            #     raise InvalidResponseFormatError("Invalid response format: missing 'response' field")
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise RequestError(f"Request to {url} failed") from e

        end_time = time.perf_counter()
        return (end_time - start_time, prompt_length, test_number)