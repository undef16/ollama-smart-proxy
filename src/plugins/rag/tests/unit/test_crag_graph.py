"""Unit tests for CRAG (Corrective RAG) graph implementation."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List

from src.plugins.rag.infrastructure.langgraph.crag_graph import CRAGGraph, CRAGState
from src.plugins.rag.domain.entities.document import Document
from src.plugins.rag.domain.entities.query import Query


class TestCRAGGraph:
    """Test suite for CRAGGraph class."""

    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.mock_rag_repository = Mock()
        self.mock_search_service = Mock()
        self.crag_graph = CRAGGraph(self.mock_rag_repository, self.mock_search_service)

    def test_initialization(self):
        """Test CRAGGraph initialization."""
        assert self.crag_graph.rag_repository == self.mock_rag_repository
        assert self.crag_graph.search_service == self.mock_search_service
        # The graph and compiled_graph properties should be set during initialization
        # Note: self.graph might be set to the StateGraph object, while self.compiled_graph is the compiled version
        assert hasattr(self.crag_graph, 'graph')
        assert hasattr(self.crag_graph, 'compiled_graph')

    def test_run_with_empty_query_raises_error(self):
        """Test that running with empty query raises RetrievalError."""
        with pytest.raises(Exception) as exc_info:
            self.crag_graph.run("")
        
        # Should raise a RetrievalError or similar
        assert "Query text cannot be empty" in str(exc_info.value)

    def test_run_with_whitespace_query_raises_error(self):
        """Test that running with whitespace-only query raises RetrievalError."""
        with pytest.raises(Exception) as exc_info:
            self.crag_graph.run("   ")
        
        assert "Query text cannot be empty" in str(exc_info.value)

    def test_retrieve_node(self):
        """Test the _retrieve_node method."""
        # Setup
        mock_document = Mock(spec=Document)
        mock_document.content = "test content"
        self.mock_rag_repository.query.return_value = [mock_document]
        
        initial_state: CRAGState = {
            "query": "test query",
            "documents": [],
            "relevant_documents": [],
            "web_documents": [],
            "context": "",
            "web_search_attempts": 0
        }

        # Execute
        result = self.crag_graph._retrieve_node(initial_state)

        # Assert
        assert result["documents"] == [mock_document]
        assert result["query"] == "test query"
        self.mock_rag_repository.query.assert_called_once()

    def test_grade_node(self):
        """Test the _grade_node method."""
        # Setup
        mock_document = Mock(spec=Document)
        mock_document.content = "test content"
        initial_state: CRAGState = {
            "query": "test query",
            "documents": [mock_document],
            "relevant_documents": [],
            "web_documents": [],
            "context": "",
            "web_search_attempts": 0
        }

        # Execute
        result = self.crag_graph._grade_node(initial_state)

        # Assert
        assert "relevant_documents" in result
        assert result["query"] == "test query"

    def test_should_web_search_no_relevant_docs(self):
        """Test _should_web_search returns 'transform_query' when no relevant documents."""
        state: CRAGState = {
            "query": "test query",
            "documents": [Mock()],
            "relevant_documents": [],
            "web_documents": [],
            "context": "",
            "web_search_attempts": 0
        }

        result = self.crag_graph._should_web_search(state)
        assert result == "transform_query"

    def test_should_web_search_has_relevant_docs(self):
        """Test _should_web_search returns 'inject' when relevant documents exist."""
        mock_doc = Mock()
        state: CRAGState = {
            "query": "test query",
            "documents": [Mock()],
            "relevant_documents": [mock_doc],
            "web_documents": [],
            "context": "",
            "web_search_attempts": 0
        }

        result = self.crag_graph._should_web_search(state)
        assert result == "inject"

    def test_transform_query_node(self):
        """Test the _transform_query_node method."""
        initial_state: CRAGState = {
            "query": "original query",
            "documents": [],
            "relevant_documents": [],
            "web_documents": [],
            "context": "",
            "web_search_attempts": 0
        }

        # Execute
        result = self.crag_graph._transform_query_node(initial_state)

        # Assert
        assert "query" in result
        # The query might be transformed, but should still be present
        assert isinstance(result["query"], str)

    def test_web_search_node(self):
        """Test the _web_search_node method."""
        mock_web_doc = Mock(spec=Document)
        mock_web_doc.content = "web content"
        self.mock_search_service.search.return_value = [mock_web_doc]
        
        initial_state: CRAGState = {
            "query": "test query",
            "documents": [],
            "relevant_documents": [],
            "web_documents": [],
            "context": "",
            "web_search_attempts": 0
        }

        # Execute
        result = self.crag_graph._web_search_node(initial_state)

        # Assert
        assert result["web_documents"] == [mock_web_doc]
        assert result["query"] == "test query"
        self.mock_search_service.search.assert_called_once_with("test query")

    def test_grade_web_node(self):
        """Test the _grade_web_node method."""
        mock_web_doc = Mock(spec=Document)
        mock_web_doc.content = "web content"
        
        initial_state: CRAGState = {
            "query": "test query",
            "documents": [],
            "relevant_documents": [],
            "web_documents": [mock_web_doc],
            "context": "",
            "web_search_attempts": 0
        }

        # Execute
        result = self.crag_graph._grade_web_node(initial_state)

        # Assert
        assert "web_documents" in result
        assert "web_search_attempts" in result

    def test_should_retry_or_inject_has_web_docs(self):
        """Test _should_retry_or_inject returns 'inject' when web documents exist."""
        mock_doc = Mock()
        state: CRAGState = {
            "query": "test query",
            "documents": [],
            "relevant_documents": [],
            "web_documents": [mock_doc],
            "context": "",
            "web_search_attempts": 0
        }

        result = self.crag_graph._should_retry_or_inject(state)
        assert result == "inject"

    def test_should_retry_or_inject_no_web_docs_max_attempts(self):
        """Test _should_retry_or_inject returns 'inject' when max attempts reached."""
        state: CRAGState = {
            "query": "test query",
            "documents": [],
            "relevant_documents": [],
            "web_documents": [],
            "context": "",
            "web_search_attempts": 3  # Max attempts
        }

        result = self.crag_graph._should_retry_or_inject(state)
        assert result == "inject"

    def test_should_retry_or_inject_no_web_docs_under_max_attempts(self):
        """Test _should_retry_or_inject returns 'transform_query' when under max attempts."""
        state: CRAGState = {
            "query": "test query",
            "documents": [],
            "relevant_documents": [],
            "web_documents": [],
            "context": "",
            "web_search_attempts": 1  # Under max attempts
        }

        result = self.crag_graph._should_retry_or_inject(state)
        assert result == "transform_query"

    def test_inject_node_with_documents(self):
        """Test the _inject_node method with documents."""
        mock_doc = Mock(spec=Document)
        mock_doc.content = "document content"
        
        initial_state: CRAGState = {
            "query": "test query",
            "documents": [mock_doc],
            "relevant_documents": [mock_doc],
            "web_documents": [],
            "context": "",
            "web_search_attempts": 0
        }

        # Execute
        result = self.crag_graph._inject_node(initial_state)

        # Assert
        assert "context" in result
        assert isinstance(result["context"], str)
        assert len(result["context"]) > 0

    def test_inject_node_without_documents(self):
        """Test the _inject_node method without documents (passthrough case)."""
        initial_state: CRAGState = {
            "query": "test query",
            "documents": [],
            "relevant_documents": [],
            "web_documents": [],
            "context": "",
            "web_search_attempts": 0
        }

        # Execute
        result = self.crag_graph._inject_node(initial_state)

        # Assert
        assert result["context"] == ""

    def test_grade_documents_empty_documents(self):
        """Test _grade_documents with empty documents list."""
        result = self.crag_graph._grade_documents([], "test query")
        assert result == []

    def test_handle_web_search_attempts_with_relevant_docs(self):
        """Test _handle_web_search_attempts with relevant documents."""
        mock_doc = Mock()
        initial_state: CRAGState = {
            "query": "test query",
            "documents": [],
            "relevant_documents": [],
            "web_documents": [],
            "context": "",
            "web_search_attempts": 1
        }

        result = self.crag_graph._handle_web_search_attempts(initial_state, [mock_doc])

        # Should reset attempts to 0 when relevant docs found
        assert result["web_search_attempts"] == 0
        assert result["web_documents"] == [mock_doc]

    def test_handle_web_search_attempts_without_relevant_docs(self):
        """Test _handle_web_search_attempts without relevant documents."""
        initial_state: CRAGState = {
            "query": "test query",
            "documents": [],
            "relevant_documents": [],
            "web_documents": [],
            "context": "",
            "web_search_attempts": 1
        }

        result = self.crag_graph._handle_web_search_attempts(initial_state, [])

        # Should increment attempts when no relevant docs found
        assert result["web_search_attempts"] == 2
        assert result["web_documents"] == []

    def test_method_existence(self):
        """Test that expected methods exist and verify the correct structure."""
        # Verify that the expected methods exist
        assert hasattr(self.crag_graph, '_transform_query_node')
        assert hasattr(self.crag_graph, '_grade_web_node')
        assert hasattr(self.crag_graph, '_should_retry_or_inject')
        assert hasattr(self.crag_graph, '_inject_node')  # The actual method that handles passthrough logic
        
        # Verify that the deprecated/non-existent _passthrough_node does not exist
        # (This addresses the terminal script's check)
        assert not hasattr(self.crag_graph, '_passthrough_node')
        
        # Verify other expected methods exist
        assert hasattr(self.crag_graph, '_retrieve_node')
        assert hasattr(self.crag_graph, '_grade_node')
        assert hasattr(self.crag_graph, '_web_search_node')
        assert hasattr(self.crag_graph, '_should_web_search')
        assert hasattr(self.crag_graph, '_handle_web_search_attempts')


class TestCRAGState:
    """Test suite for CRAGState TypedDict."""
    
    def test_crag_state_structure(self):
        """Test that CRAGState has the expected fields."""
        state: CRAGState = {
            "query": "test query",
            "documents": [],
            "relevant_documents": [],
            "web_documents": [],
            "context": "",
            "web_search_attempts": 0
        }
        
        assert "query" in state
        assert "documents" in state
        assert "relevant_documents" in state
        assert "web_documents" in state
        assert "context" in state
        assert "web_search_attempts" in state
        
        assert state["query"] == "test query"
        assert state["documents"] == []
        assert state["relevant_documents"] == []
        assert state["web_documents"] == []
        assert state["context"] == ""
        assert state["web_search_attempts"] == 0

        assert state["web_search_attempts"] == 0