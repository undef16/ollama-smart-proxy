# Data Model: Optimizer Agent

**Date**: 2026-01-01 | **Designer**: Kilo Code

## Overview

The Optimizer Agent requires persistent storage for learning from request patterns and storing optimization statistics. This document defines the data structures and database schema.

## Database Schema

### SQLite Database: optimizer_stats.db

Located at `src/plugins/optimizer/data/optimizer_stats.db`

#### Table: templates

Stores information about detected prompt templates and their optimal parameters.

```sql
CREATE TABLE templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_hash TEXT UNIQUE NOT NULL,  -- Unique identifier for template
    working_window INTEGER NOT NULL,     -- Current optimal context window size
    observation_count INTEGER DEFAULT 0, -- Number of times this template observed
    avg_distance REAL DEFAULT 0.0,       -- Average Hamming distance for matches
    fingerprint_64 INTEGER,              -- 64-bit SimHash fingerprint
    fingerprint_128 INTEGER,             -- 128-bit SimHash fingerprint
    fingerprint_256 INTEGER,             -- 256-bit SimHash fingerprint
    fingerprint_512 INTEGER,             -- 512-bit SimHash fingerprint
    fingerprint_1024 INTEGER,            -- 1024-bit SimHash fingerprint
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_template_hash ON templates(template_hash);
CREATE INDEX idx_fingerprint_64 ON templates(fingerprint_64);
CREATE INDEX idx_fingerprint_128 ON templates(fingerprint_128);
```

#### Table: request_stats

Stores performance metrics for each request to enable learning.

```sql
CREATE TABLE request_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER REFERENCES templates(id),
    prompt_hash TEXT NOT NULL,           -- Hash of full prompt for deduplication
    latency REAL NOT NULL,               -- Response time in seconds
    tokens_input INTEGER NOT NULL,       -- Input token count
    tokens_context INTEGER NOT NULL,     -- Context window size used
    tokens_output INTEGER,               -- Output token count (if available)
    quality_score REAL,                  -- Quality metric (0.0-1.0, if computed)
    model TEXT NOT NULL,                 -- LLM model used
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for analytics
CREATE INDEX idx_template_id ON request_stats(template_id);
CREATE INDEX idx_timestamp ON request_stats(timestamp);
CREATE INDEX idx_model ON request_stats(model);
```

#### Table: optimization_rules

Stores learned optimization rules (future extension).

```sql
CREATE TABLE optimization_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER REFERENCES templates(id),
    param_name TEXT NOT NULL,            -- e.g., 'num_ctx', 'num_batch'
    param_value TEXT NOT NULL,           -- Parameter value
    confidence REAL DEFAULT 0.0,         -- Confidence in this rule (0.0-1.0)
    success_count INTEGER DEFAULT 0,     -- Times this rule improved performance
    total_count INTEGER DEFAULT 0,       -- Total times this rule was applied
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_template_param ON optimization_rules(template_id, param_name);
```

## Data Structures

### In-Memory Objects

#### TemplateInfo

```python
@dataclass
class TemplateInfo:
    template_hash: str
    working_window: int
    observation_count: int
    avg_distance: float
    fingerprints: Dict[int, int]  # resolution -> fingerprint
    created_at: datetime
    updated_at: datetime
```

#### RequestMetrics

```python
@dataclass
class RequestMetrics:
    latency: float
    tokens_input: int
    tokens_context: int
    tokens_output: Optional[int]
    quality_score: Optional[float]
    model: str
    timestamp: datetime
```

#### OptimizationContext

```python
@dataclass
class OptimizationContext:
    template_id: Optional[int]
    applied_params: Dict[str, Any]  # e.g., {'num_ctx': 1024, 'num_batch': 8}
    confidence: float
    reasoning: str  # For logging/debugging
```

## Data Flow

### Request Processing

1. **Input Analysis**: Extract prompt from context
2. **Template Matching**: Query templates table for SimHash matches
3. **Parameter Selection**: Retrieve optimal parameters from matched template
4. **Optimization Application**: Modify context with selected parameters
5. **Metric Collection**: Store request stats after response

### Learning Process

1. **Post-Response**: Calculate metrics (latency, token counts)
2. **Template Update**: Update fingerprint via majority voting
3. **Rule Learning**: Analyze performance patterns for future optimization
4. **Cleanup**: Periodic removal of low-confidence templates

## Performance Considerations

### Database Optimization

- Use WAL mode for concurrent reads/writes
- Batch inserts for bulk operations
- Connection pooling for multiple requests
- Regular VACUUM for space reclamation

### Memory Management

- Cache frequently accessed templates in memory
- Limit in-memory template count (LRU eviction)
- Lazy loading of fingerprints

### Scalability

- Support for multiple models via model column
- Template hashing for efficient lookups
- Configurable retention policies for old data

## Migration Strategy

### Initial Schema

Start with basic tables (templates, request_stats) for MVP functionality.

### Future Extensions

Add optimization_rules table for advanced learning.
Add indexes as query patterns emerge.
Consider partitioning by time for large datasets.

## Validation

### Data Integrity

- Foreign key constraints enforce referential integrity
- UNIQUE constraints prevent duplicate templates
- NOT NULL constraints on required fields

### Consistency Checks

- Validate fingerprint resolutions match configuration
- Ensure working_window is within model limits
- Check quality_score bounds (0.0-1.0)