# Data Model

**Feature**: RAG Plugin for Ollama Smart Proxy  
**Date**: 2026-01-08  

## Overview

This document defines the core data entities and their relationships for the RAG plugin implementation. All entities follow domain-driven design principles with clear validation rules and relationships.

## Core Entities

### Query

Represents a user query that triggers the RAG process.

**Attributes**:
- `id`: UUID - Unique identifier
- `text`: str - The original query text (max 1000 chars)
- `timestamp`: datetime - When the query was received
- `processed`: bool - Whether the query has been processed
- `user_id`: str - Identifier of the user (from proxy context)

**Validation Rules**:
- Text must not be empty
- Text must start with "/rag " prefix (handled by proxy)
- Timestamp must be in UTC

**Relationships**:
- 1:N with Document (retrieved documents for this query)
- 1:1 with RelevanceScore (overall score for the query)

### Document

Represents a piece of retrieved context from either local knowledge base or web search.

**Attributes**:
- `id`: UUID - Unique identifier
- `content`: str - The document text content
- `source`: str - Source identifier ("local" or "web")
- `url`: str (optional) - Web URL if from search
- `title`: str (optional) - Document title
- `query_id`: UUID - Reference to the query that retrieved this document
- `timestamp`: datetime - When the document was retrieved

**Validation Rules**:
- Content must not be empty
- Source must be either "local" or "web"
- URL required if source is "web"

**Relationships**:
- N:1 with Query
- 1:1 with RelevanceScore (individual score)

### RelevanceScore

Represents the relevance evaluation of a document or query.

**Attributes**:
- `id`: UUID - Unique identifier
- `score`: float - Numerical relevance score (0.0 to 1.0)
- `threshold`: float - Threshold used for evaluation (default 0.6)
- `evaluation_method`: str - Method used ("llm" or "hybrid")
- `document_id`: UUID (optional) - Reference to document if individual score
- `query_id`: UUID (optional) - Reference to query if aggregate score
- `timestamp`: datetime - When the score was calculated

**Validation Rules**:
- Score must be between 0.0 and 1.0
- Threshold must be between 0.0 and 1.0
- Must reference either document or query (not both)

**Relationships**:
- 1:1 with Document (if individual score)
- 1:1 with Query (if aggregate score)

### KnowledgeGraph

Represents the graph structure stored in Neo4j.

**Attributes**:
- `id`: UUID - Unique identifier
- `name`: str - Graph name/namespace
- `node_count`: int - Number of nodes
- `edge_count`: int - Number of relationships
- `last_updated`: datetime - Last modification time
- `schema_version`: str - Version of the graph schema

**Validation Rules**:
- Name must be unique
- Counts must be non-negative
- Schema version follows semantic versioning

**Relationships**:
- 1:N with Document (documents stored in this graph)

### VectorEmbedding

Represents vector embeddings stored in PostgreSQL.

**Attributes**:
- `id`: UUID - Unique identifier
- `vector`: list[float] - The embedding vector (dimension depends on model)
- `document_id`: UUID - Reference to the source document
- `model`: str - Embedding model used (e.g., "text-embedding-ada-002")
- `dimension`: int - Vector dimension
- `timestamp`: datetime - When the embedding was created

**Validation Rules**:
- Vector must not be empty
- Dimension must match vector length
- Model must be a supported embedding model

**Relationships**:
- N:1 with Document

## Entity Relationships Diagram

```
Query
├── 1:N Document
├── 1:1 RelevanceScore (aggregate)
└── 1:N VectorEmbedding (through Document)

Document
├── 1:1 RelevanceScore (individual)
├── 1:N VectorEmbedding
└── N:1 KnowledgeGraph

KnowledgeGraph
└── 1:N Document
```

## Data Flow

1. **Query Ingestion**: Query entity created from user input
2. **Retrieval**: Documents retrieved and linked to query
3. **Scoring**: RelevanceScore entities created for each document
4. **Storage**: VectorEmbedding and KnowledgeGraph entities updated
5. **Response**: Query marked as processed with final context

## Validation Constraints

- All entities must have valid UUIDs
- Timestamps must be in UTC and not in the future
- String fields have reasonable length limits
- Numeric fields have appropriate ranges
- Foreign key relationships must be maintained
- Cascade delete rules: deleting Query deletes related Documents and Scores

## Performance Considerations

- Query-Document relationship should support efficient bulk retrieval
- RelevanceScore queries need indexing on score and threshold
- VectorEmbedding storage should use optimized PostgreSQL vector extensions
- KnowledgeGraph operations should minimize Cypher query complexity