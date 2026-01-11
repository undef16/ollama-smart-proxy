from abc import ABC, abstractmethod
from typing import List

from src.plugins.rag.domain.entities.document import Document
from src.plugins.rag.domain.entities.query import Query


class RagRepository(ABC):
    """
    Abstract interface for RAG data operations.

    This port defines the contract for interacting with the RAG knowledge base,
    providing methods to query, store, and retrieve documents in a technology-agnostic way.
    """

    @abstractmethod
    def query(self, query: Query) -> List[Document]:
        """
        Query the RAG knowledge base for relevant documents.

        Args:
            query: The user query to search for relevant documents.

        Returns:
            A list of relevant documents retrieved from the knowledge base.
        """
        pass

    @abstractmethod
    def store_documents(self, documents: List[Document]) -> None:
        """
        Store a list of documents in the RAG knowledge base.

        Args:
            documents: The list of documents to store.
        """
        pass

    @abstractmethod
    def get_documents(self, query: Query) -> List[Document]:
        """
        Retrieve documents based on the given query.

        Args:
            query: The query criteria for retrieving documents.

        Returns:
            A list of documents matching the query criteria.
        """
        pass