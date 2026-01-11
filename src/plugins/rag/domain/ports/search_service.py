from abc import ABC, abstractmethod
from typing import List

from src.plugins.rag.domain.entities.document import Document


class SearchService(ABC):
    """
    Abstract interface for external search operations.

    This port defines the contract for performing web searches using external services
    like SearxNG, providing a technology-agnostic way to retrieve documents from the web.
    """

    @abstractmethod
    def search(self, query: str) -> List[Document]:
        """
        Perform a web search for the given query.

        Args:
            query: The search query string.

        Returns:
            A list of documents retrieved from the external search service.
        """
        pass