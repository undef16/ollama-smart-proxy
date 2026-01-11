# Agent Contract: RAG Plugin

**Feature**: RAG Plugin for Ollama Smart Proxy  
**Date**: 2026-01-08  
**Contract Version**: 1.0.0  

## Overview

This contract defines the interface that the RAG plugin must implement to integrate with the Ollama Smart Proxy. The plugin follows the hexagonal architecture pattern with clear ports and adapters.

## Plugin Interface

### Base Plugin Contract

All plugins must implement the `BaseAgent` interface:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from shared.base_agent import BaseAgent

class RagAgent(BaseAgent):
    """RAG Plugin implementation for Ollama Smart Proxy"""

    @abstractmethod
    async def on_retrieve(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming request and enhance with RAG context"""
        pass

    @abstractmethod
    async def on_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process outgoing response (no-op for RAG)"""
        pass
```

### Request/Response Contracts

#### Input Request Format

```python
{
    "id": "string",  # Unique request ID
    "prompt": "string",  # User prompt, starts with "/rag "
    "model": "string",  # Ollama model name
    "stream": boolean,  # Whether response should be streamed
    "user_id": "string",  # User identifier from proxy
    "timestamp": "2023-01-01T00:00:00Z",  # ISO 8601 timestamp
    "metadata": {
        "temperature": float,
        "max_tokens": int,
        "other_params": {...}
    }
}
```

#### Enhanced Request Format (After RAG Processing)

```python
{
    "id": "string",
    "prompt": "string",  # Original prompt with injected context
    "model": "string",
    "stream": boolean,
    "user_id": "string",
    "timestamp": "2023-01-01T00:00:00Z",
    "metadata": {
        "temperature": float,
        "max_tokens": int,
        "rag_context": {
            "query": "string",  # Processed query without /rag prefix
            "documents": [
                {
                    "content": "string",
                    "source": "local|web",
                    "url": "string"  # optional
                }
            ],
            "search_performed": boolean,
            "processing_time_ms": int
        },
        "other_params": {...}
    }
}
```

#### Response Format

```python
{
    "id": "string",
    "model": "string",
    "response": "string",  # Ollama response
    "done": boolean,
    "context": [...],  # Ollama context
    "total_duration": int,  # nanoseconds
    "load_duration": int,
    "prompt_eval_count": int,
    "eval_count": int,
    "eval_duration": int,
    "timestamp": "2023-01-01T00:00:00Z"
}
```

## Domain Ports

### RagRepository Port

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities import Query, Document

class RagRepository(ABC):
    """Port for RAG data persistence"""

    @abstractmethod
    async def save_query(self, query: Query) -> None:
        """Save query entity"""
        pass

    @abstractmethod
    async def get_query(self, query_id: str) -> Optional[Query]:
        """Retrieve query by ID"""
        pass

    @abstractmethod
    async def save_documents(self, documents: List[Document]) -> None:
        """Save retrieved documents"""
        pass

    @abstractmethod
    async def get_relevant_documents(self, query: str, threshold: float = 0.6) -> List[Document]:
        """Get relevant documents for query"""
        pass
```

### SearchService Port

```python
from abc import ABC, abstractmethod
from typing import List

class SearchService(ABC):
    """Port for external search functionality"""

    @abstractmethod
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Perform web search and return results"""
        pass

    @abstractmethod
    async def transform_query(self, query: str) -> str:
        """Transform query for optimal search performance"""
        pass
```

## Error Contracts

### Error Response Format

```python
{
    "error": {
        "type": "string",  # "validation_error", "service_unavailable", "processing_error"
        "message": "string",  # Human-readable error message
        "details": {...},  # Optional error details
        "retryable": boolean  # Whether the request can be retried
    },
    "id": "string",
    "timestamp": "2023-01-01T00:00:00Z"
}
```

### Error Types

- `validation_error`: Invalid input parameters
- `service_unavailable`: External service (Neo4j, PostgreSQL, SearxNG) unavailable
- `processing_error`: Internal processing failure
- `timeout_error`: Request processing exceeded time limits

## Configuration Contract

### Environment Variables

```python
# Database connections
NEO4J_URI: str = "bolt://localhost:7687"
POSTGRES_URI: str = "postgresql://user:pass@localhost:5432/rag"

# External services
SEARXNG_HOST: str = "http://localhost:8080"
OLLAMA_BASE_URL: str = "http://localhost:11434"

# RAG parameters
RAG_THRESHOLD: float = 0.6
RAG_MAX_DOCUMENTS: int = 5
RAG_TIMEOUT_SECONDS: int = 30
```

### Plugin Configuration

```python
{
    "name": "rag",
    "version": "1.0.0",
    "description": "RAG enhancement plugin for Ollama Smart Proxy",
    "command_prefix": "/rag",
    "priority": 10,  # Plugin execution priority
    "enabled": true
}
```

## Performance Contracts

### Latency Requirements

- Local RAG queries: < 5 seconds
- Web search fallback: < 10 seconds
- Concurrent requests: Support 100 simultaneous queries

### Resource Usage

- Memory: < 500MB per plugin instance
- CPU: < 20% average utilization
- Network: Minimal external calls for local queries

## Testing Contracts

### Unit Test Requirements

- All domain entities must have validation tests
- All ports must have mock implementations
- LangGraph state transitions must be tested
- Error handling paths must be covered

### Integration Test Requirements

- End-to-end RAG pipeline testing
- Database connectivity testing
- External service mocking
- Performance benchmarking

### Contract Test Requirements

- Plugin interface compliance
- Request/response format validation
- Error handling verification