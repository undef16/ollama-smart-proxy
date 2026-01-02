# Agent Contract: OptimizerAgent

**Version**: 1.0 | **Date**: 2026-01-01

## Overview

This contract defines the interface and behavior of the OptimizerAgent class, which implements the BaseAgent interface for dynamic LLM parameter optimization.

## Class Definition

```python
class OptimizerAgent(BaseAgent):
    """Intelligent agent for optimizing LLM inference parameters."""

    @property
    def name(self) -> str:
        """Returns 'opt' for slash command activation."""
        return "opt"

    async def on_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process request context before Ollama forwarding.

        Args:
            context: Request context with keys:
                - 'messages': List of message dicts (chat) or 'prompt': str (generate)
                - 'model': str - LLM model name
                - 'stream': bool - streaming flag
                - Other Ollama-compatible parameters

        Returns:
            Modified context with optimized parameters added/updated.

        Raises:
            No exceptions - must handle errors gracefully
        """
        pass

    async def on_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process response context after Ollama response.

        Args:
            context: Response context with keys:
                - 'response': Ollama response dict
                - 'agents': List of applied agent names

        Returns:
            Unmodified context (response processing is for learning only).

        Raises:
            No exceptions - must handle errors gracefully
        """
        pass
```

## Context Modifications

### Request Context Input

**Chat Requests**:
```python
{
    "model": "llama2",
    "messages": [
        {"role": "user", "content": "/opt Tell me about AI"},
        {"role": "assistant", "content": "AI is..."}
    ],
    "stream": false,
    "options": {}  # May contain existing Ollama options
}
```

**Generate Requests**:
```python
{
    "model": "llama2",
    "prompt": "/opt Write a Python hello world",
    "stream": false,
    "options": {}
}
```

### Request Context Output

**Modified Context**:
```python
{
    "model": "llama2",
    "messages": [
        {"role": "user", "content": "Tell me about AI"},  # /opt removed
        {"role": "assistant", "content": "AI is..."}
    ],
    "stream": false,
    "options": {
        "num_ctx": 1024,      # Added/optimized
        "num_batch": 8,       # Added/optimized
        # ... other optimized parameters
    },
    "_optimizer": {  # Internal metadata
        "template_id": 123,
        "confidence": 0.85,
        "reasoning": "Matched template with 12 observations"
    }
}
```

## Response Context

### Input

**Chat Response**:
```python
{
    "response": {
        "message": {
            "role": "assistant",
            "content": "AI stands for Artificial Intelligence..."
        },
        "done": true,
        "total_duration": 1500000000,  # nanoseconds
        "eval_count": 150,
        "eval_duration": 1400000000
    },
    "agents": ["opt"]
}
```

**Generate Response**:
```python
{
    "response": {
        "response": "print('Hello, World!')",
        "done": true,
        "total_duration": 800000000,
        "eval_count": 80,
        "eval_duration": 750000000
    },
    "agents": ["opt"]
}
```

### Output

Response context is returned unmodified. All learning happens internally.

## Error Handling

- **Database Errors**: Log and continue with default parameters
- **SimHash Errors**: Log and skip template matching
- **Invalid Context**: Log and return context unchanged
- **Performance Issues**: Implement timeouts and circuit breakers

## Thread Safety

- Agent instances are singleton (PluginRegistry pattern)
- Database connections must be thread-safe
- No shared mutable state between requests

## Performance Requirements

- **Request Processing**: <100ms overhead
- **Memory Usage**: <50MB per agent instance
- **Concurrent Requests**: Support 100+ simultaneous optimizations
- **Database Queries**: <10ms average response time

## Testing Contracts

### Unit Tests

- Mock database for isolated testing
- Test SimHash logic with known inputs
- Verify parameter calculations
- Test error handling paths

### Integration Tests

- Full request/response cycle with real database
- Template learning verification
- Performance regression checks
- Concurrent request handling

## Dependencies

- **Internal**: BaseAgent, logging
- **External**: sqlite3, hashlib, asyncio
- **Optional**: psutil for system metrics