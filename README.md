# Ollama Smart Proxy

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A lightweight, async proxy server for Ollama that provides OpenAI-compatible APIs with extensible agent-based request/response processing.

## Features

- **OpenAI-Compatible API**: Drop-in replacement for OpenAI chat completions
- **Dynamic Model Loading**: Automatically pulls and loads models as needed
- **Agent System**: Extensible plugin architecture for custom request/response processing
- **Slash Commands**: Activate agents directly in prompts (e.g., `/rag`, `/example`)
- **Pass-through Endpoints**: Direct access to Ollama's native APIs
- **Health Monitoring**: Built-in health checks for proxy and upstream status
- **Async Performance**: Fully asynchronous with connection pooling and caching
- **Plugin Introspection**: Runtime inspection of loaded agents

## Architecture

The project follows a vertical slice architecture with a shared kernel:

- **Shared Kernel**: Common services (config, logging, Ollama client, plugin registry)
- **Slices**: Independent feature areas (chat, generate, health, passthrough, plugins)
- **Plugins**: Extensible agent system loaded from `src/plugins/`

## Quick Start

See [docs/quickstart.md](docs/quickstart.md) for detailed setup and usage instructions.

### Basic Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start the proxy
python main.py

# Test with curl
curl -X POST "http://localhost:11555/api/chat/" \
     -H "Content-Type: application/json" \
     -d '{"model": "qwen2.5-coder:1.5b", "messages": [{"role": "user", "content": "Hello!"}]}'
```

## API Endpoints

### Chat Completions
- `POST /api/chat/` - OpenAI-compatible chat completions with agent support

### Text Generation
- `POST /api/generate/` - Text generation with agent support

### Health & Monitoring
- `GET /health` - Health check for proxy and upstream Ollama
- `GET /plugins` - List loaded agent plugins

### Pass-through Endpoints
- `GET /api/tags` - List available models
- `POST /api/embeddings` - Generate embeddings

## Configuration

Configure via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_PROXY_OLLAMA_HOST` | `localhost` | Ollama server host |
| `OLLAMA_PROXY_OLLAMA_PORT` | `11434` | Ollama server port |
| `OLLAMA_PROXY_PLUGINS_DIR` | `src/plugins` | Agent plugins directory |

## Development

### Prerequisites

- Python 3.12+
- Ollama server running locally
- pytest for testing

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/unit/      # Unit tests
pytest tests/integration/  # Integration tests
```

### Project Structure

```
main.py                     # Application entry point

src/
├── shared/                 # Shared kernel
│   ├── config.py          # Configuration management
│   ├── logging.py         # Logging setup
│   ├── ollama_client.py   # Async Ollama client
│   └── plugin_registry.py # Agent loading and management
├── slices/                 # Feature slices
│   ├── chat/              # Chat completions
│   ├── generate/          # Text generation
│   ├── health/            # Health monitoring
│   ├── passthrough/       # Ollama API pass-through
│   └── plugins/           # Plugin introspection
└── plugins/               # Agent plugins directory
    └── example_agent/     # Example agent implementation

tests/
├── unit/                  # Unit tests
├── integration/           # Integration tests
└── contract/              # Contract tests

docs/                      # Documentation
specs/                     # Feature specifications
```

### Adding Agents

Create a new directory under `src/plugins/` with an `agent.py` file:

```python
from src.shared.base_agent import BaseAgent

class MyAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "myagent"

    async def on_request(self, context):
        # Pre-process request
        return context

    async def on_response(self, context):
        # Post-process response
        return context
```

Agents are activated via slash commands in user messages: `/myagent Hello world`

## Available Plugins

The proxy comes with several built-in plugins that demonstrate the agent system's capabilities:

### Optimizer Plugin
Intelligent agent that dynamically optimizes LLM inference parameters based on prompt similarity detection and historical performance data using SimHash algorithms. Provides 20-50% faster response times for recurring patterns.

**Usage:** `/opt Tell me about machine learning algorithms`

See [`src/plugins/optimizer/README.md`](src/plugins/optimizer/README.md) for details.

### RAG Plugin
Retrieval-Augmented Generation plugin that enhances AI responses by retrieving relevant context from a local knowledge base and falling back to web search when necessary, implementing the Corrective RAG (CRAG) pattern.

**Usage:** `/rag What is the capital of France?`

See [`src/plugins/rag/README.md`](src/plugins/rag/README.md) for details.


## Performance

- **Async I/O**: All operations are fully asynchronous
- **Model Caching**: 5-minute cache for model availability checks
- **Connection Pooling**: Efficient HTTP client connection reuse
- **Lazy Loading**: Models pulled only when needed

## Principles

This project follows software engineering best practices:

- **OOP**: Object-oriented design with proper encapsulation
- **DRY**: No code duplication, reusable components
- **KISS**: Simple, maintainable architecture
- **Async**: Fully asynchronous for performance

## Contributing

1. Follow the established patterns and principles
2. Add comprehensive tests for new features
3. Update documentation as needed
4. Ensure all tests pass before submitting

## License

MIT License - see [LICENSE](LICENSE) for details.