# RAG Plugin for Ollama Smart Proxy

## Overview

The RAG (Retrieval-Augmented Generation) Plugin is an advanced agent for the Ollama Smart Proxy that implements the Corrective RAG (CRAG) pattern. It enhances AI responses by retrieving relevant context from a local knowledge base and falling back to web search when necessary, providing more accurate and contextually rich answers.

This plugin integrates seamlessly with the Ollama Smart Proxy architecture, activating on `/rag` commands to augment prompts with retrieved information before forwarding them to the Ollama API.

## Features

- **Corrective RAG (CRAG) Implementation**: Uses LangGraph as a state machine to orchestrate retrieval, relevance evaluation, and corrective actions.
- **Multi-Source Retrieval**: Combines local knowledge graph/vector search with external web search via SearxNG.
- **Hexagonal Architecture**: Clean separation of concerns with domain, infrastructure, and adapter layers.
- **Resilient Design**: Includes circuit breakers, performance monitoring, and comprehensive error handling.
- **Configurable Thresholds**: Adjustable relevance scores and fallback mechanisms.
- **Caching**: Built-in caching for improved performance and reduced latency.
- **Comprehensive Testing**: Unit and integration tests covering all components.

## Architecture

The plugin follows hexagonal architecture principles:

```
src/plugins/rag/
├── agent.py              # Main RagAgent class and entry point
├── config.json           # Configuration settings
├── domain/               # Business logic and entities
│   ├── entities/         # Domain models (Document, Query, RelevanceScore)
│   └── ports/            # Interfaces for external dependencies
├── infrastructure/       # External concerns and implementations
│   ├── adapters/         # Adapters for LightRAG and SearxNG
│   ├── config.py         # Configuration management
│   ├── langgraph/        # CRAG graph implementation
│   ├── cache/            # Caching mechanisms
│   ├── monitoring/       # Performance monitoring
│   ├── resilience/       # Circuit breaker and error handling
│   └── utils/            # Utility functions
└── tests/                # Unit and integration tests
```

### Key Components

- **RagAgent**: Main agent class that handles `/rag` command processing.
- **CRAGGraph**: LangGraph-based state machine implementing the CRAG pattern.
- **LightRAGAdapter**: Interface to LightRAG for local knowledge retrieval.
- **SearxNGAdapter**: Interface to SearxNG for web search fallback.
- **ConfigurationManager**: Manages plugin configuration from `config.json`.

### Algorithm Overview

The RAG agent implements the Corrective RAG (CRAG) algorithm using a state machine approach:

1. **Retrieve**: Query the local knowledge base (LightRAG) for relevant documents based on the user query.

2. **Grade**: Evaluate document relevance using an LLM (configured model) to score documents from 0.0 to 1.0. Documents scoring above the threshold (default 0.9) are considered relevant.

3. **Decision Point**: If relevant documents are found, proceed to context injection. If not, transform the query for better web search results.

4. **Transform Query**: Use LLM to rephrase the query into a more effective search query for web engines.

5. **Web Search**: Perform external web search using SearxNG to retrieve additional context.

6. **Grade Web Results**: Evaluate the relevance of web search results using the same LLM grading process.

7. **Retry Logic**: If web results are relevant, proceed to injection. If not, retry with a new transformed query (up to 3 attempts). After maximum attempts, proceed with available context or empty context.

8. **Inject**: Assemble the final context from all relevant documents (local + web) and format it using the configured system context template for injection into the Ollama prompt.

The algorithm ensures robust retrieval by combining local knowledge with web search fallbacks, while using LLM-based grading for quality control and query transformation for improved search effectiveness.

## Dependencies

- Python 3.12+
- LightRAG
- LangGraph
- LangChain
- Pydantic
- Neo4j (for graph storage)
- PostgreSQL (for vector and key-value storage)
- psycopg2-binary
- requests

## Configuration

The plugin is configured via `config.json`. Key settings include:

```json
{
  "lightrag_host": "http://localhost:9621",
  "lightrag_api_key": "",
  "neo4j_uri": "bolt://192.168.1.138:7687",
  "postgres_uri": "postgresql://ollama_proxy:pass@192.168.1.138:5432/rag_db",
  "searxng_host": "http://192.168.1.138:8080",
  "rag_threshold": 0.9,
  "max_documents": 5,
  "timeout": 30,
  "cache_ttl": 3600,
  "cache_size": 1000,
  "embedding_model": "nomic-embed-text:latest",
  "llm_model": "qwen2.5-coder:1.5b",
  "working_dir": "./rag_data",
  "kv_storage": "RedisKVStorage",
  "vector_storage": "PGVectorStorage",
  "graph_storage": "Neo4JStorage",
  "doc_status_storage": "PGDocStatusStorage",
  "circuit_breaker_failure_threshold": 5,
  "circuit_breaker_recovery_timeout": 60.0,
  "circuit_breaker_success_threshold": 3,
  "default_relevance_score": 0.5,
  "max_query_length": 500,
  "system_context": "You have access to the following relevant information:\n\n{context}\n\nBased on the above information, please assist with the user's request: {query}",
  "relevance_evaluation_prompt_template": "...",
  "query_transformation_prompt_template": "...",
  "searxng_safesearch": 1
}
```

### Setup Requirements

1. **LightRAG Server**: Ensure LightRAG is running on the configured host.
2. **Neo4j Database**: Set up Neo4j for graph storage.
3. **PostgreSQL Database**: Configure PostgreSQL for vector and document status storage.
4. **SearxNG Instance**: Deploy SearxNG for web search capabilities.
5. **Ollama**: Ensure Ollama is accessible for embedding and LLM operations.

## Usage

### Activating the Plugin

The RAG plugin activates when a request contains a `/rag` command. It processes both chat messages and generate prompts.

### Example Usage

**Chat Request:**
```json
{
  "messages": [
    {"role": "user", "content": "/rag What is the capital of France?"}
  ]
}
```

**Generate Request:**
```json
{
  "prompt": "/rag Explain quantum computing"
}
```

The plugin will:
1. Extract the query from the request.
2. Retrieve relevant context from the local knowledge base.
3. Evaluate relevance; if below threshold (0.9), perform web search.
4. Inject the retrieved context into the prompt using the configured template.
5. Forward the enriched request to Ollama.

### Response Processing

The plugin currently passes through responses unchanged, as RAG augmentation occurs on the request side.

## Development

### Running Tests

```bash
cd src
pytest plugins/rag/tests/
```

### Code Quality

```bash
cd src
ruff check plugins/rag/
```

### Building and Deployment

The plugin integrates with the main Ollama Smart Proxy application. Ensure all dependencies are installed and configurations are set before deployment.

## Monitoring and Logging

The plugin includes comprehensive logging and performance monitoring:

- Structured logging with configurable levels.
- Performance metrics for retrieval operations.
- Circuit breaker status monitoring.
- Error handling with graceful degradation.

## Contributing

When contributing to the RAG plugin:

1. Follow the hexagonal architecture principles.
2. Add unit tests for new functionality.
3. Update configuration documentation for new settings.
4. Ensure compatibility with the base agent interface.

## License

This plugin is part of the Ollama Smart Proxy project. See the main project LICENSE for details.