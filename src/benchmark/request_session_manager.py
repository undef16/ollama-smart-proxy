"""Manages HTTP request sessions with retry logic."""
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .constants import BenchmarkConstants


# Configure logging
logger = logging.getLogger(__name__)


class RequestSessionManager:
    """Manages HTTP request sessions with retry logic."""
    
    @staticmethod
    def create_session_with_retries(max_retries: int = -1) -> requests.Session:
        """Create a requests session with retry strategy."""
        if max_retries == -1:
            max_retries = BenchmarkConstants.DEFAULT_MAX_RETRIES
        session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session