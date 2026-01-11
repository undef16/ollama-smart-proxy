"""LightRAG adapter implementation for RAG repository port using REST API."""

from typing import List, Optional
import requests
from requests.exceptions import RequestException

from src.plugins.rag.domain.entities.document import Document
from src.plugins.rag.domain.entities.query import Query
from src.plugins.rag.domain.ports.rag_repository import RagRepository
from src.plugins.rag.infrastructure.config import ConfigurationManager
from src.plugins.rag.infrastructure.logging import (
    LoggingUtils, ExternalServiceError, NetworkError,
    ValidationError
)
from src.plugins.rag.infrastructure.error_handler import ErrorHandler

logger = LoggingUtils.get_rag_logger(__name__)


class LightRAGAdapter(RagRepository):
    """Adapter for LightRAG knowledge base operations using REST API."""

    def __init__(self, lightrag_host: Optional[str] = None, timeout: int = 30):
        """Initialize the LightRAG adapter.

        Args:
            lightrag_host: URL of the LightRAG server. If None, uses config.
            timeout: Request timeout in seconds.
        """
        if lightrag_host is None:
            config = ConfigurationManager.get_config()
            lightrag_host = config.lightrag_host
            timeout = config.timeout

        self.lightrag_host = lightrag_host.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        logger.debug(f"LightRAG adapter initialized with host: {self.lightrag_host}")

    def _get_headers(self) -> dict:
        """Get request headers including API key if configured."""
        config = ConfigurationManager.get_config()
        headers = {"Content-Type": "application/json"}
        if config.lightrag_api_key:
            headers["X-API-Key"] = config.lightrag_api_key
        return headers

    @classmethod
    def create_from_config(cls) -> 'LightRAGAdapter':
        """Create LightRAG adapter from configuration.

        Returns:
            Configured LightRAGAdapter instance.
        """
        config = ConfigurationManager.get_config()
        return cls(lightrag_host=config.lightrag_host, timeout=config.timeout)

    @ErrorHandler.log_error_context("lightrag_query", component="lightrag_adapter")
    @ErrorHandler.retry_on_failure(max_attempts=3, delay=1.0, backoff=2.0,
                                   exceptions=(RequestException, NetworkError))
    @ErrorHandler.with_fallback(fallback_value=[])
    def query(self, query: Query) -> List[Document]:
        """Query the RAG knowledge base for relevant documents.

        Args:
            query: The user query to search for relevant documents.

        Returns:
            A list of relevant documents retrieved from the knowledge base.

        Raises:
            ExternalServiceError: If LightRAG service is unavailable
            NetworkError: If network connectivity fails
            ValidationError: If query validation fails
        """
        # Validate input
        if not query or not query.text.strip():
            error = ValidationError(
                "Query text cannot be empty",
                field="query.text",
                value=query.text if query else None,
                suggestions=["Provide a non-empty query text"]
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

        config = ConfigurationManager.get_config()
        if len(query.text.strip()) > config.max_query_length:
            error = ValidationError(
                "Query text too long",
                field="query.text",
                value=f"length: {len(query.text)}",
                suggestions=[f"Shorten the query to under {config.max_query_length} characters"]
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

        try:
            # Call LightRAG REST API with include_references, include_chunk_content, and enable_rerank
            # to retrieve the actual documents/chunks used for answer generation with reranking
            url = f"{self.lightrag_host}/query"
            params = {
                "query": query.text,
                "mode": "mix",
                "include_references": True,
                "include_chunk_content": True,
                "enable_rerank": True
            }

            logger.info(f"Querying LightRAG with: {query.text}")
            response = self.session.post(
                url,
                json=params,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            # Parse the response into Document entities
            documents = []

            # Extract references (retrieved chunks with content)
            references = data.get("references", [])

            if references:
                # Use references to create Document objects
                config = ConfigurationManager.get_config()
                for i, ref in enumerate(references):
                    file_path = ref.get("file_path", f"lightrag_ref_{i}")
                    contents = ref.get("content", [])

                    for j, content in enumerate(contents):
                        doc = Document(
                            content=content,
                            source=file_path,
                            metadata={
                                "reference_id": ref.get("reference_id", str(i)),
                                "chunk_index": j,
                                "query": query.text,
                                "mode": "mix"
                            }
                        )
                        documents.append(doc)

            if not documents:
                # If no references, try to use context
                context = data.get("context") or data.get("response")
                if context:
                    logger.info("No references found, using context as document")
                    if isinstance(context, list):
                        context = "\n\n".join(str(c) for c in context)

                    doc = Document(
                        content=str(context),
                        source="lightrag_context",
                        metadata={
                            "query": query.text,
                            "mode": "mix",
                            "type": "context"
                        }
                    )
                    documents.append(doc)
                else:
                    # No references available, return empty list
                    logger.info("No references or context returned from LightRAG, returning empty document list")
                    return []

            logger.info(f"Retrieved {len(documents)} documents from LightRAG")
            return documents

        except requests.Timeout as e:
            error = NetworkError(
                f"LightRAG request timed out after {self.timeout}s",
                url=self.lightrag_host,
                timeout=self.timeout,
                suggestions=[
                    "Increase timeout value",
                    "Check LightRAG service performance",
                    "Verify network latency"
                ],
                cause=e
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

        except requests.HTTPError as e:
            status_code = response.status_code if 'response' in locals() else 'unknown'
            error = ExternalServiceError(
                f"LightRAG API returned HTTP {status_code}: {e}",
                service_name="lightrag",
                operation="api_request",
                suggestions=[
                    f"Check LightRAG service status (HTTP {status_code})",
                    "Verify API endpoint and parameters",
                    "Check LightRAG service logs"
                ],
                cause=e
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

        except RequestException as e:
            error = NetworkError(
                f"LightRAG network error: {str(e)}",
                url=self.lightrag_host,
                suggestions=[
                    "Check network connectivity",
                    "Verify LightRAG host configuration",
                    "Check proxy settings"
                ],
                cause=e
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

        except Exception as e:
            error = ExternalServiceError(
                f"LightRAG query operation failed: {str(e)}",
                service_name="lightrag",
                operation="query",
                suggestions=[
                    "Check LightRAG service configuration",
                    "Review LightRAG logs for errors",
                    "Verify API compatibility"
                ],
                cause=e
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

    @ErrorHandler.log_error_context("lightrag_store_documents", component="lightrag_adapter")
    @ErrorHandler.retry_on_failure(max_attempts=3, delay=1.0, backoff=2.0,
                                   exceptions=(RequestException, NetworkError))
    @ErrorHandler.with_fallback(fallback_value=None)
    def store_documents(self, documents: List[Document]) -> None:
        """Store a list of documents in the RAG knowledge base.

        Args:
            documents: The list of documents to store.

        Raises:
            ExternalServiceError: If LightRAG service is unavailable
            NetworkError: If network connectivity fails
            ValidationError: If document validation fails
        """
        if not documents:
            logger.debug("No documents to store")
            return

        try:
            logger.info(f"Storing {len(documents)} documents in LightRAG")

            # Insert documents one by one using the /documents/text endpoint
            for doc in documents:
                if not doc.content or not doc.content.strip():
                    logger.warning("Skipping document with empty content")
                    continue

                url = f"{self.lightrag_host}/documents/text"
                payload = {
                    "text": doc.content,
                    "description": doc.source
                }

                response = self.session.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=self.timeout
                )
                response.raise_for_status()

                # Optionally track the response for debugging
                data = response.json()
                track_id = data.get("track_id")
                logger.debug(f"Document stored with track_id: {track_id}")

            logger.info("Documents stored successfully in LightRAG")

        except requests.Timeout as e:
            error = NetworkError(
                f"LightRAG request timed out after {self.timeout}s",
                url=self.lightrag_host,
                timeout=self.timeout,
                suggestions=[
                    "Increase timeout value",
                    "Check LightRAG service performance",
                    "Verify network latency"
                ],
                cause=e
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

        except requests.HTTPError as e:
            status_code = response.status_code if 'response' in locals() else 'unknown'
            error = ExternalServiceError(
                f"LightRAG API returned HTTP {status_code}: {e}",
                service_name="lightrag",
                operation="api_request",
                suggestions=[
                    f"Check LightRAG service status (HTTP {status_code})",
                    "Verify API endpoint and parameters",
                    "Check LightRAG service logs"
                ],
                cause=e
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

        except RequestException as e:
            error = NetworkError(
                f"LightRAG network error: {str(e)}",
                url=self.lightrag_host,
                suggestions=[
                    "Check network connectivity",
                    "Verify LightRAG host configuration",
                    "Check proxy settings"
                ],
                cause=e
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

        except Exception as e:
            error = ExternalServiceError(
                f"LightRAG store operation failed: {str(e)}",
                service_name="lightrag",
                operation="store_documents",
                suggestions=[
                    "Check LightRAG service configuration",
                    "Review LightRAG logs for errors",
                    "Verify API compatibility"
                ],
                cause=e
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

    @ErrorHandler.log_error_context("lightrag_get_documents", component="lightrag_adapter")
    def get_documents(self, query: Query) -> List[Document]:
        """Retrieve documents based on the given query.

        Args:
            query: The query criteria for retrieving documents.

        Returns:
            A list of documents matching the query criteria.
        """
        # For LightRAG, get_documents uses the same query endpoint with references
        return self.query(query)
