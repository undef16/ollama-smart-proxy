"""SearxNG adapter implementation for external web search."""

import logging
from typing import List, Optional
import requests

from src.plugins.rag.domain.entities.document import Document
from src.plugins.rag.domain.ports.search_service import SearchService
from src.plugins.rag.infrastructure.config import ConfigurationManager
from src.plugins.rag.infrastructure.resilience import (
    CircuitBreakerRegistry,
    CircuitBreakerOpenException
)
from src.plugins.rag.infrastructure.logging import (
    LoggingUtils, ExternalServiceError, NetworkError,
    ErrorCategory, ErrorSeverity, ValidationError
)
from src.plugins.rag.infrastructure.error_handler import ErrorHandler

logger = LoggingUtils.get_rag_logger(__name__)


class SearxNGAdapter(SearchService):
    """Adapter for SearxNG external web search operations."""

    def __init__(self, searxng_host: Optional[str] = None, timeout: int = 30):
        """Initialize the SearxNG adapter.

        Args:
            searxng_host: URL of the SearxNG instance. If None, uses config.
            timeout: Request timeout in seconds.
        """
        if searxng_host is None:
            config = ConfigurationManager.get_config()
            searxng_host = config.searxng_host
            timeout = config.timeout

        self.searxng_host = searxng_host.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

        # Initialize circuit breaker for SearxNG service
        config = ConfigurationManager.get_config()
        self.circuit_breaker = CircuitBreakerRegistry.get_service_circuit_breaker(
            service_name="searxng",
            failure_threshold=config.circuit_breaker_failure_threshold,
            recovery_timeout=config.circuit_breaker_recovery_timeout,
            success_threshold=config.circuit_breaker_success_threshold,
            timeout=timeout
        )

        logger.debug(f"SearxNG adapter initialized with host: {self.searxng_host}")

    @classmethod
    def create_from_config(cls) -> 'SearxNGAdapter':
        """Create SearxNG adapter from configuration.

        Returns:
            Configured SearxNGAdapter instance.
        """
        config = ConfigurationManager.get_config()
        return cls(searxng_host=config.searxng_host, timeout=config.timeout)

    @ErrorHandler.log_error_context("searxng_search", component="searxng_adapter")
    @ErrorHandler.retry_on_failure(max_attempts=3, delay=1.0, backoff=2.0,
                                   exceptions=(requests.RequestException, NetworkError))
    @ErrorHandler.with_fallback(fallback_value=[])
    def search(self, query: str) -> List[Document]:
        """Perform a web search using SearxNG.

        Args:
            query: The search query string.

        Returns:
            A list of documents retrieved from SearxNG.

        Raises:
            ExternalServiceError: If SearxNG service is unavailable
            NetworkError: If network connectivity fails
            ValidationError: If query validation fails
        """
        # Validate input
        if not query or not query.strip():
            error = ValidationError(
                "Search query cannot be empty",
                field="query",
                value=query,
                suggestions=["Provide a non-empty search query"]
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

        config = ConfigurationManager.get_config()
        if len(query.strip()) > config.max_query_length:
            error = ValidationError(
                "Search query too long",
                field="query",
                value=f"length: {len(query)}",
                suggestions=[f"Shorten the query to under {config.max_query_length} characters"]
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

        try:
            # Use circuit breaker to protect the search operation
            return self.circuit_breaker.call(self._perform_search, query)

        except CircuitBreakerOpenException as e:
            # Circuit breaker is open, provide fallback behavior
            error = ExternalServiceError(
                "SearxNG service circuit breaker is open",
                service_name="searxng",
                operation="search",
                suggestions=[
                    "SearxNG service is temporarily unavailable",
                    "Using fallback: returning empty results",
                    "Check service status and try again later"
                ],
                cause=e
            )
            LoggingUtils.log_structured_error(error, logger)
            return []  # Return empty list as fallback

        except requests.RequestException as e:
            # Network-level error
            error = NetworkError(
                f"SearxNG network request failed: {str(e)}",
                url=self.searxng_host,
                timeout=self.timeout,
                suggestions=[
                    "Check SearxNG service availability",
                    "Verify network connectivity",
                    "Check proxy/firewall settings"
                ],
                cause=e
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

        except Exception as e:
            # Generic error
            error = ExternalServiceError(
                f"SearxNG search operation failed: {str(e)}",
                service_name="searxng",
                operation="search",
                suggestions=[
                    "Check SearxNG service configuration",
                    "Review SearxNG logs for errors",
                    "Verify API compatibility"
                ],
                cause=e
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

    def _perform_search(self, query: str) -> List[Document]:
        """Internal method to perform the actual search (protected by circuit breaker).

        Args:
            query: The search query string.

        Returns:
            A list of documents retrieved from SearxNG.

        Raises:
            ExternalServiceError: If SearxNG API returns an error
            NetworkError: If network request fails
        """
        logger.debug(f"Performing SearxNG search for query: {query}")

        # Prepare the search URL
        search_url = f"{self.searxng_host}/search"
        config = ConfigurationManager.get_config()
        params = {
            'q': query,
            'format': 'json',
            'safesearch': config.searxng_safesearch,  # Safe search level from config
        }

        try:
            # Make the request
            response = self.session.get(
                search_url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

        except requests.Timeout as e:
            error = NetworkError(
                f"SearxNG request timed out after {self.timeout}s",
                url=search_url,
                timeout=self.timeout,
                suggestions=[
                    "Increase timeout value",
                    "Check SearxNG service performance",
                    "Verify network latency"
                ],
                cause=e
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

        except requests.HTTPError as e:
            status_code = response.status_code if 'response' in locals() else 'unknown'
            error = ExternalServiceError(
                f"SearxNG API returned HTTP {status_code}: {e}",
                service_name="searxng",
                operation="api_request",
                suggestions=[
                    f"Check SearxNG service status (HTTP {status_code})",
                    "Verify API endpoint and parameters",
                    "Check SearxNG service logs"
                ],
                cause=e
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

        except requests.RequestException as e:
            error = NetworkError(
                f"SearxNG network error: {str(e)}",
                url=search_url,
                suggestions=[
                    "Check network connectivity",
                    "Verify SearxNG host configuration",
                    "Check proxy settings"
                ],
                cause=e
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

        try:
            # Parse the response
            data = response.json()
            results = data.get('results', [])

            if not isinstance(results, list):
                error = ExternalServiceError(
                    "SearxNG API returned invalid response format",
                    service_name="searxng",
                    operation="response_parsing",
                    suggestions=[
                        "Check SearxNG API version compatibility",
                        "Verify response format expectations",
                        "Contact SearxNG service administrator"
                    ]
                )
                LoggingUtils.log_structured_error(error, logger)
                raise error

        except ValueError as e:
            error = ExternalServiceError(
                "Failed to parse SearxNG JSON response",
                service_name="searxng",
                operation="json_parsing",
                suggestions=[
                    "Check SearxNG API response format",
                    "Verify JSON parsing compatibility",
                    "Check for API changes"
                ],
                cause=e
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

        # Convert results to Document objects
        documents = []
        for i, result in enumerate(results):
            try:
                content = result.get('content', '')
                if not content:
                    logger.debug(f"Skipping SearxNG result {i}: no content")
                    continue  # Skip results without content

                document = Document(
                    content=content,
                    source=result.get('url', ''),
                    metadata={
                        'title': result.get('title', ''),
                        'engines': result.get('engines', []),
                        'query': query,
                        'search_engine': 'searxng',
                        'result_index': i
                    }
                )
                documents.append(document)

            except Exception as e:
                logger.warning(f"Failed to process SearxNG result {i}: {e}")
                # Continue processing other results
                continue

        logger.info(f"Successfully retrieved {len(documents)} documents from SearxNG")
        return documents