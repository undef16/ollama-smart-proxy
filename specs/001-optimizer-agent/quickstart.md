# Quick Start: Optimizer Agent Plugin

**Version**: 1.0 | **Date**: 2026-01-01

## Overview

The Optimizer Agent automatically optimizes LLM inference parameters for better performance while maintaining response quality. It learns from request patterns and adapts context windows using SimHash-based template detection.

## Installation

The plugin is automatically loaded if present in `src/plugins/optimizer/agent.py`.

### Dependencies

Add to `pyproject.toml` optional dependencies:

```toml
[project.optional-dependencies]
optimizer = [
    "psutil>=5.9.0",  # System metrics
]
```

Install with: `pip install -e ".[optimizer]"`

## Configuration

### Plugin Configuration (Optional)

Create `src/plugins/optimizer/config.json`:

```json
{
  "enabled": true,
  "simhash": {
    "bit_length": 64,
    "window_sizes": [64, 128, 256, 512, 1024],
    "hamming_thresholds": {
      "64": 3,
      "128": 4,
      "256": 6,
      "512": 8,
      "1024": 12
    }
  },
  "optimization": {
    "default_buffer_multiplier": 1.3,
    "max_context_window": 4096,
    "min_context_window": 512,
    "batch_size_options": [1, 2, 4, 8, 16]
  },
  "storage": {
    "db_path": "data/optimizer_stats.db",
    "retention_days": 30
  }
}
```

## Usage

### Basic Usage

Add `/opt` to your chat messages:

```
User: /opt Tell me about machine learning
Assistant: [Optimized response with adapted parameters]
```

### Generate Requests

```
User: /opt Write a Python function to calculate fibonacci numbers
Assistant: [Optimized code generation]
```

### Advanced Usage

The agent works automatically:

1. **First Request**: Analyzes prompt, applies basic optimizations
2. **Repeated Patterns**: Learns optimal settings for similar prompts
3. **Template Detection**: Adapts context window based on prompt structure

## Monitoring

### Logs

Check application logs for optimization details:

```
INFO: Processing request with optimizer agent
INFO: Matched template hash: abc123, applying window: 1024
INFO: Optimization saved 200ms latency
```

### Database Inspection

Query the SQLite database:

```sql
-- View learned templates
SELECT template_hash, working_window, observation_count
FROM templates
ORDER BY observation_count DESC;

-- Check recent optimizations
SELECT timestamp, latency, tokens_input, model
FROM request_stats
ORDER BY timestamp DESC
LIMIT 10;
```

## Performance Expectations

- **Speed Improvement**: 20-50% faster responses for optimized requests
- **Quality Maintenance**: 90%+ similarity to baseline responses
- **Template Detection**: 80% accuracy for repeated patterns
- **Overhead**: <100ms analysis time per request

## Troubleshooting

### Common Issues

1. **No Optimization Applied**
   - Check logs for "No matching template found"
   - First requests use default parameters
   - Ensure `/opt` command is present

2. **Poor Performance**
   - Verify database is writable
   - Check system resources (CPU/memory)
   - Review configuration parameters

3. **Template Not Detected**
   - Prompts must be sufficiently similar (Hamming distance < threshold)
   - Increase observation count for better matching
   - Check SimHash configuration

### Debug Mode

Enable detailed logging by setting log level to DEBUG:

```python
import logging
logging.getLogger('optimizer_agent').setLevel(logging.DEBUG)
```

## Examples

### Chat Optimization

```bash
curl -X POST http://localhost:11555/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "messages": [
      {"role": "user", "content": "/opt Explain quantum computing"}
    ]
  }'
```

### Template Learning

After several similar requests:

```sql
SELECT template_hash, working_window, observation_count
FROM templates
WHERE observation_count > 5;
```

Output:
```
template_hash    working_window    observation_count
abc123def        2048             12
def456ghi        1024             8
```

## Uninstallation

Remove the `src/plugins/optimizer/` directory to disable the plugin. The database can be safely deleted if learning should reset.