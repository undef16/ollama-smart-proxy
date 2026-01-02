# Research: SimHash Algorithm for Prompt Template Detection

**Date**: 2026-01-01 | **Researcher**: Kilo Code

## Overview

This research investigates SimHash as a mechanism for detecting similar prompt templates in LLM requests to enable adaptive context window sizing. The goal is to identify efficient, lightweight implementations suitable for real-time request processing.

## SimHash Fundamentals

### What is SimHash?

SimHash is a locality-sensitive hashing algorithm that produces fingerprints for documents/text that are similar if their Hamming distance is small. It's particularly effective for:

- Near-duplicate detection
- Large-scale similarity search
- Template/pattern recognition in text

### How SimHash Works

1. **Tokenization**: Break text into tokens (words, n-grams, or shingles)
2. **Hashing**: Hash each token to a bit vector
3. **Weighting**: Apply weights (e.g., TF-IDF) to token hashes
4. **Aggregation**: Sum weighted vectors across all tokens
5. **Fingerprint**: Convert to binary fingerprint by sign of each dimension

### Key Properties

- **Similarity Preservation**: Similar documents have small Hamming distance
- **Compact**: 64-128 bit fingerprints
- **Fast**: O(n) time complexity where n is document length
- **Memory Efficient**: Fixed-size fingerprints regardless of input size

## Application to Prompt Templates

### Use Case Analysis

For LLM prompt optimization, we need to:

1. Detect when new prompts match known "templates" (recurring patterns)
2. Adapt context window based on historical optimal settings for similar prompts
3. Handle variable parts (e.g., different names in similar email templates)

### Multi-Resolution Approach

Implement SimHash at multiple prefix lengths to find the "stable" portion:

- Compute fingerprints for prefixes of varying lengths (64, 128, 256, 512, 1024 tokens)
- Match against stored templates starting from longest prefix
- Use first successful match as the "working window" size

### Template Learning

- Store representative fingerprints per template
- Use majority voting for fingerprint updates
- Track observation counts and success rates
- Adapt working window size based on match consistency

## Implementation Options

### Option 1: simhash-py Library

```python
from simhash import Simhash

# Simple usage
hash1 = Simhash('text1').value
hash2 = Simhash('text2').value
distance = bin(hash1 ^ hash2).count('1')  # Hamming distance
```

**Pros**: Ready-to-use, optimized C extensions
**Cons**: Additional dependency, may not support custom tokenization

### Option 2: Manual Implementation

```python
import hashlib
from typing import List

def simhash(tokens: List[str], hashbits: int = 64) -> int:
    v = [0] * hashbits
    for token in tokens:
        h = int(hashlib.md5(token.encode()).hexdigest()[:16], 16)
        for i in range(hashbits):
            bit = (h >> i) & 1
            v[i] += 1 if bit else -1
    fingerprint = 0
    for i in range(hashbits):
        if v[i] >= 0:
            fingerprint |= (1 << i)
    return fingerprint
```

**Pros**: No external deps, full control, lightweight
**Cons**: Manual optimization needed

### Recommendation

Use manual implementation with hashlib for minimal dependencies. The algorithm is straightforward and performs well for our use case.

## Performance Considerations

### Computational Overhead

- SimHash computation: O(n) where n = number of tokens
- Hamming distance: O(1) for fixed bit length
- Template matching: O(t) where t = number of stored templates

### Memory Usage

- Fingerprints: 8-16 bytes per template per resolution level
- Storage: SQLite can handle thousands of templates efficiently

### Optimization Strategies

- Use shingles (3-5 tokens) for robustness
- Cache tokenization results
- Index templates for fast candidate retrieval (future enhancement)

## Integration with Agent Architecture

### Request Processing Flow

1. Parse incoming prompt
2. Compute multi-resolution SimHash fingerprints
3. Query database for matching templates
4. Apply learned parameters if match found
5. Store/update statistics post-response

### Database Schema

```sql
CREATE TABLE templates (
    id INTEGER PRIMARY KEY,
    template_hash TEXT UNIQUE,
    working_window INTEGER,
    observation_count INTEGER,
    fingerprint_64 INTEGER,
    fingerprint_128 INTEGER,
    -- etc for other resolutions
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE request_stats (
    id INTEGER PRIMARY KEY,
    template_id INTEGER REFERENCES templates(id),
    latency REAL,
    tokens_input INTEGER,
    tokens_output INTEGER,
    quality_score REAL,
    timestamp TIMESTAMP
);
```

## Conclusion

SimHash is well-suited for prompt template detection with acceptable performance overhead. Manual implementation provides sufficient functionality without additional dependencies. Multi-resolution approach enables adaptive window sizing based on template stability.