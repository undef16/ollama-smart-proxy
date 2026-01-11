# Quick Start Guide: RAG Plugin

**Feature**: RAG Plugin for Ollama Smart Proxy  
**Date**: 2026-01-08  
**Version**: 1.0.0  

## Overview

This guide provides step-by-step instructions for setting up and using the RAG plugin for Ollama Smart Proxy. The plugin enhances AI responses with relevant context from local knowledge bases and web search using the Corrective RAG (CRAG) pattern with LightRAG and LangGraph. It includes resilience features like circuit breakers and comprehensive monitoring capabilities.

## Prerequisites

### System Requirements

- Python 3.12+
- Docker and Docker Compose
- 16GB RAM minimum (for all services)
- 20GB free disk space

### What's Included

This setup provides a complete RAG-enabled Ollama Smart Proxy environment with:

- **Ollama Smart Proxy** with RAG plugin
- **Neo4j** (Graph database for knowledge representation)
- **PostgreSQL** with pgvector (Vector database for embeddings)
- **SearxNG** (Privacy-focused meta search engine)
- **Redis** (Caching and session storage)
- **pgAdmin** (Database administration)
- **Redis Insight** (Redis management UI)

## Installation

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/undef16/ollama-smart-proxy.git
cd ollama-smart-proxy

# Install Python dependencies
pip install -r requirements.txt

# Install RAG plugin dependencies
pip install lightrag langgraph langchain pydantic neo4j psycopg2-binary requests
```

### 2. Start Database Services with Docker Compose

```bash
# Start all database and search services
docker-compose up -d

# Wait for services to be healthy (may take 2-3 minutes)
docker-compose ps
```

### 3. Create Plugin Configuration

Create the RAG plugin configuration file with the correct default values based on actual implementation (note the updated storage drivers and models):

```bash
# Create config file with correct defaults
cat > src/plugins/rag/config.json << EOF
{
  "neo4j_uri": "bolt://localhost:7687",
  "postgres_uri": "postgresql://ollama_proxy:pass@localhost:5432/rag_db",
  "searxng_host": "http://localhost:8080",
  "ollama_base_url": "http://localhost:11434",
  "rag_threshold": 0.6,
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
  "doc_status_storage": "PGDocStatusStorage"
}
EOF
```

### 4. Setup Ollama Locally

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull required models
ollama pull qwen2.5-coder:1.5b
ollama pull nomic-embed-text:latest
```

### 5. Verify Services

```bash
# Check service status
docker-compose ps

# Test individual services
curl http://localhost:7474  # Neo4j Browser
curl http://localhost:5432  # PostgreSQL (will fail, but port open)
curl http://localhost:8080  # SearxNG
curl http://localhost:11434/api/tags  # Ollama
curl http://localhost:11555/health  # Proxy
```

### 6. Access Management Interfaces

- **Neo4j Browser**: http://localhost:7474 (user: neo4j, password: password)
- **pgAdmin**: http://localhost:5050 (user: pgadmin4@pgadmin.org, password: admin)
- **Redis Insight**: http://localhost:5540
- **SearxNG**: http://localhost:8080

## Usage

### 1. Start the Proxy

```bash
# Start the proxy with RAG plugin enabled
python main.py
```

### 2. Basic RAG Query

```bash
# Use curl to send a RAG-enhanced request
curl -X POST http://localhost:11555/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:1.5b",
    "prompt": "/rag What is machine learning?",
    "stream": false
  }'
```

### 3. Chat API with RAG

```bash
# Send chat messages with RAG context
curl -X POST http://localhost:11555/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:1.5b",
    "messages": [
      {
        "role": "user",
        "content": "/rag Explain how neural networks work"
      }
    ]
  }'
```

### 4. Expected Response

```json
{
  "model": "qwen2.5-coder:1.5b",
  "response": "Machine learning is a subset of artificial intelligence...",
  "context": "[Document 1]\nContent about machine learning...\n[Document 2]\nMore context...\n",
  "rag_metadata": {
    "documents_used": 3,
    "search_performed": false,
    "processing_time_ms": 1250
  }
}
```

## Configuration Options

### Complete Configuration Reference

The RAG plugin configuration includes the following options with their default values and descriptions. These settings are stored in `src/plugins/rag/config.json` and loaded via the `RAGConfig` model using Pydantic validation.

#### Database and Service Configuration
- `neo4j_uri` (default: `"bolt://localhost:7687"`): Neo4j connection URI for graph storage
- `postgres_uri` (default: `"postgresql://ollama_proxy:pass@localhost:5432/rag_db"`): PostgreSQL connection URI for vector storage
- `searxng_host` (default: `"http://localhost:8080"`): SearxNG host URL for web search fallback
- `ollama_base_url` (default: `"http://localhost:11434"`): Ollama base URL for LLM operations

#### RAG Processing Configuration
- `rag_threshold` (default: `0.6`): Relevance threshold for document acceptance (0.0-1.0)
- `max_documents` (default: `5`): Maximum number of documents to retrieve and inject
- `timeout` (default: `30`): Timeout in seconds for external service calls
- `cache_ttl` (default: `3600`): Cache TTL in seconds for query results
- `cache_size` (default: `1000`): Maximum number of cache entries

#### Model Configuration
- `embedding_model` (default: `"nomic-embed-text:latest"`): Model for generating embeddings
- `llm_model` (default: `"qwen2.5-coder:1.5b"`): Model for LLM operations including document grading

#### Storage Configuration
- `working_dir` (default: `"./rag_data"`): Working directory for RAG data files
- `kv_storage` (default: `"RedisKVStorage"`): Key-value storage type for LightRAG
- `vector_storage` (default: `"PGVectorStorage"`): Vector storage type for embeddings
- `graph_storage` (default: `"Neo4JStorage"`): Graph storage type for knowledge graph
- `doc_status_storage` (default: `"PGDocStatusStorage"`): Document status storage type

### Configuration Management

The RAG plugin uses a singleton `ConfigurationManager` that validates configuration settings using Pydantic models. Configuration can be modified by editing the JSON file and restarting the service or by using the configuration reload functionality if implemented in your deployment system.
```

## CRAG Pipeline Architecture

The RAG plugin implements a Corrective RAG (CRAG) pattern using LangGraph with the following nodes and workflow flow:

### Pipeline Components

1. **Retrieve Node**: Uses LightRAG to retrieve relevant documents from the knowledge base using mixed-mode search (graph + vector)
2. **Grade Node**: Uses the configured LLM to grade document relevance with scores between 0.0-1.0
3. **Conditional Logic**: If no documents meet the relevance threshold, proceed to web search
4. **Transform Query Node**: Enhances the query for better web search results
5. **Web Search Node**: Uses SearxNG for privacy-focused web search fallback
6. **Inject Node**: Combines relevant local and web documents into context for injection

### Circuit Breaker Protection

The plugin includes circuit breakers for external services (Ollama and SearxNG) with the following configuration defaults:
- **Failure threshold**: 5 consecutive failures before opening circuit
- **Recovery timeout**: 60 seconds before attempting reset
- **Success threshold**: 3 successful calls to close circuit from half-open state
- **Request timeout**: 30 seconds for service calls

### Resilience Features

- **Circuit Breakers**: Prevent cascading failures when external services become unavailable
- **Retry Logic**: Automatic retries with exponential backoff for transient failures
- **Fallback Behavior**: Graceful degradation when services are unavailable
- **Timeout Handling**: Prevents hanging requests with configurable timeouts

## Performance Tuning

### Database Optimization

```sql
-- PostgreSQL vector indexing for better performance
CREATE INDEX IF NOT EXISTS idx_rag_documents_embedding ON rag_documents USING ivfflat (embedding vector_cosine_ops);

-- Neo4j indexing for faster graph queries
CREATE INDEX idx_document_content IF NOT EXISTS FOR (d:Document) ON (d.content);
CREATE INDEX idx_document_id IF NOT EXISTS FOR (d:Document) ON (d.id);
```

### Caching

The plugin includes built-in caching for:
- Query results
- Document embeddings
- Search results
- LLM grading responses

Configure cache settings in the configuration file:
```json
{
  "cache_ttl": 3600,  // 1 hour TTL for cache entries
  "cache_size": 1000  // Maximum 100 cache entries
}
```

### Performance Monitoring

The plugin includes a comprehensive `PerformanceMonitor` that tracks metrics including:
- Operation timing (with p50, p95, p99 percentiles)
- Success/failure rates
- Concurrency levels (current and peak)
- Histograms of response times
- Uptime and overall system health

### Resource Optimization

- **Batch Processing**: The system processes documents in batches to optimize throughput
- **Sampling**: For high-volume deployments, metrics sampling is available to reduce overhead
- **Connection Pooling**: Database connections are pooled to reduce connection overhead
- **Memory Management**: Efficient memory usage with bounded deques for metrics storage

## Monitoring

### Health Checks

```bash
# Proxy health endpoint
curl http://localhost:11555/health

# Ollama health
curl http://localhost:11434/api/tags

# Individual service health
docker-compose exec postgres pg_isready -U ollama_proxy
docker-compose exec neo4j cypher-shell -u neo4j -p password "MATCH () RETURN count(*) limit 1;"
```

### Metrics

The plugin exposes comprehensive metrics via the performance monitoring system. Key metrics include:
- `rag_queries_total`: Total RAG queries processed
- `rag_search_fallback_total`: Web search fallbacks performed
- `rag_processing_duration`: Query processing time (p50, p95, p99)
- `rag_concurrent_requests`: Current number of concurrent requests
- `rag_peak_concurrency`: Peak concurrent request count
- `rag_success_rate`: Overall success rate for operations

### Performance Summary

To view detailed performance metrics, use the performance monitor's summary function. This will show operation timing, success rates, concurrency levels, and histogram data for response times across all components of the CRAG pipeline.

### Circuit Breaker Status

Monitor circuit breaker status to detect when external services (Ollama, SearxNG) become unavailable. The system provides detailed status information including state changes, failure counts, and recovery attempts for each service with circuit breaker protection.

## Troubleshooting

### Common Issues

#### Service Startup Issues

```bash
# Check all service status
docker-compose ps

# View service logs
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]
```

#### Database Connection Errors

```bash
# Check Neo4j
curl http://localhost:7474

# Check PostgreSQL connection
docker-compose exec postgres psql -U ollama_proxy -d rag_db -c "SELECT version();"

# Check SearxNG
curl http://localhost:8080
```

#### Circuit Breaker Open

When circuit breakers open due to service failures, you'll see `CircuitBreakerOpenException` in logs. To diagnose:
1. Check the target service status (Ollama or SearxNG)
2. Review service logs for errors
3. Verify network connectivity
4. Wait for the recovery timeout (default 60 seconds) or restart the failing service

#### CRAG Pipeline Failures

If the CRAG pipeline fails, check for these common issues:
1. Document grading failures due to LLM unavailability
2. LightRAG configuration issues with storage drivers
3. SearxNG search query formatting problems
4. Memory issues during document processing

#### Slow Responses

1. Ensure databases are properly indexed (see performance tuning section)
2. Check network connectivity to external services
3. Monitor system resources (CPU, memory)
4. Review the performance monitor metrics for bottlenecks
5. Consider adjusting the `max_documents` configuration to reduce processing overhead

### Debug Mode

Enable debug logging for detailed RAG operation information. The system uses structured logging with different log levels for different components of the RAG pipeline, making it easier to trace issues through the CRAG workflow. You can enable detailed logging by setting the appropriate log level in your environment or configuration file. The logging system includes special handling for different error categories (network, validation, external service, etc.) with appropriate error handling and recovery strategies.
```

## Performance Tuning

### Database Optimization

```sql
-- PostgreSQL vector indexing
CREATE INDEX ON rag_documents USING ivfflat (embedding vector_cosine_ops);

-- Neo4j indexing
CREATE INDEX ON :Document(content);
```

### Caching

The plugin includes built-in caching for:
- Query results
- Document embeddings
- Search results

Configure cache settings:

```env
RAG_CACHE_TTL=3600  # 1 hour
RAG_CACHE_SIZE=1000  # Max cache entries
```

## Monitoring

### Health Checks

```bash
# Proxy health endpoint
curl http://localhost:11555/health

# Ollama health
curl http://localhost:11434/api/tags

# Individual service health
docker-compose exec postgres pg_isready -U ollama_proxy
docker-compose exec neo4j cypher-shell -u neo4j -p password "MATCH () RETURN count(*) limit 1;"
```

### Metrics

The plugin exposes metrics at `/metrics`:

- `rag_queries_total`: Total RAG queries processed
- `rag_search_fallback_total`: Web search fallbacks
- `rag_processing_duration`: Query processing time

## Development

### Running Tests

```bash
# Unit tests
pytest src/plugins/rag/tests/unit/

# Integration tests
pytest src/plugins/rag/tests/integration/

# All tests
pytest src/plugins/rag/tests/
```

### Local Development

```bash
# Start all services
docker-compose up -d

# Run proxy in development mode with auto-reload
# (Modify main.py to use reload settings)
python main.py --reload

# Or use uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 11555
```

### Service Management

```bash
# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service-name]

# Scale services
docker-compose up -d --scale ollama-smart-proxy=2

# Clean up volumes (WARNING: destroys data)
docker-compose down -v
```

## Support

For issues and questions:
- Check the troubleshooting section above
- Review the specification: `specs/003-rag-plugin/spec.md`
- Check proxy logs for detailed error messages
- File issues on the project repository

## Next Steps

- Explore advanced configuration options
- Integrate with your existing knowledge base
- Monitor performance and adjust thresholds
- Contribute improvements back to the project