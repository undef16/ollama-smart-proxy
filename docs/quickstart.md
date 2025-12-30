# Ollama Smart Proxy Quick Start Guide

## Overview

The Ollama Smart Proxy is a lightweight proxy server that provides OpenAI-compatible APIs for Ollama models, with support for dynamic model loading and extensible agent-based request/response processing.

## Prerequisites

- Python 3.12+
- Ollama server running locally (default: http://localhost:11434)
- At least one Ollama model available

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ollama-smart-proxy
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The proxy can be configured via environment variables:

- `OLLAMA_PROXY_OLLAMA_HOST`: Ollama server host (default: localhost)
- `OLLAMA_PROXY_OLLAMA_PORT`: Ollama server port (default: 11434)
- `OLLAMA_PROXY_PLUGINS_DIR`: Directory containing agent plugins (default: src/plugins)

## Running the Proxy

Start the proxy server:

```bash
python -m src.main
```

The proxy will start on `http://localhost:11555` by default.

## Basic Usage

### Chat API

Send a chat request using OpenAI-compatible format:

```bash
curl -X POST "http://localhost:11555/api/chat/" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "qwen2.5-coder:1.5b",
       "messages": [
         {"role": "user", "content": "Hello, how are you?"}
       ]
     }'
```

### Health Check

Check the health of the proxy and upstream Ollama server:

```bash
curl http://localhost:11555/health
```

Response:
```json
{
  "status": "healthy",
  "proxy": "Ok",
  "upstream": "Ok"
}
```

### List Available Models

Get available models from Ollama:

```bash
curl http://localhost:11555/api/tags
```

### List Loaded Plugins

See which agent plugins are currently loaded:

```bash
curl http://localhost:11555/plugins
```

## Agent Activation

Activate agents using slash commands in your prompts:

```bash
curl -X POST "http://localhost:11555/api/chat/" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "qwen2.5-coder:1.5b",
       "messages": [
         {"role": "user", "content": "/example Hello with agent processing"}
       ]
     }'
```

## Pass-through Endpoints

The proxy also provides pass-through access to Ollama's native APIs:

### Text Generation

```bash
curl -X POST "http://localhost:11555/api/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "qwen2.5-coder:1.5b",
       "prompt": "Write a Python function to calculate fibonacci numbers"
     }'
```

### Embeddings

```bash
curl -X POST "http://localhost:11555/api/embeddings" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "nomic-embed-text",
       "prompt": "This is some text to embed"
     }'
```

## Development

### Running Tests

Run the test suite:

```bash
pytest
```

### Adding Custom Agents

1. Create a new directory under `src/plugins/`
2. Create an `agent.py` file implementing the `BaseAgent` interface
3. The agent will be automatically loaded on startup

Example agent structure:

```python
from src.shared.base_agent import BaseAgent

class MyAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "myagent"

    async def on_request(self, context):
        # Modify request context
        return context

    async def on_response(self, context):
        # Modify response context
        return context
```

## Troubleshooting

### Common Issues

1. **Connection refused**: Ensure Ollama server is running and accessible
2. **Model not found**: The proxy will automatically pull models when needed
3. **Plugin not loading**: Check that your agent class inherits from `BaseAgent` and has the correct structure

### Logs

Check the application logs for detailed error information. Logging level can be controlled via the `LOG_LEVEL` environment variable.