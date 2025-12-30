import asyncio
from typing import Any, Dict, List, Optional

import ollama

from .config import Config


class OllamaClient:
    """Async wrapper for the Ollama client library."""

    def __init__(self):
        config = Config()
        self._client = ollama.Client(
            host=f"http://{config.ollama_host}:{config.ollama_port}"
        )

    async def _run_sync(self, func, *args, **kwargs) -> Any:
        """Run a synchronous function in an executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        **kwargs
    ) -> Any:
        """Send a chat request to Ollama."""
        return await self._run_sync(
            self._client.chat,
            model=model,
            messages=messages,
            stream=stream,
            **kwargs
        )

    async def generate(
        self,
        model: str,
        prompt: str,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text using Ollama."""
        return await self._run_sync(
            self._client.generate,
            model=model,
            prompt=prompt,
            stream=stream,
            **kwargs
        )

    async def pull(self, model: str) -> Dict[str, Any]:
        """Pull (download) a model."""
        return await self._run_sync(self._client.pull, model)

    async def list(self) -> Dict[str, Any]:
        """List available models."""
        return await self._run_sync(self._client.list)

    async def show(self, model: str) -> Dict[str, Any]:
        """Show model information."""
        return await self._run_sync(self._client.show, model)

    async def delete(self, model: str) -> Dict[str, Any]:
        """Delete a model."""
        return await self._run_sync(self._client.delete, model)

    async def embeddings(self, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate embeddings."""
        return await self._run_sync(
            self._client.embeddings,
            model=model,
            prompt=prompt,
            **kwargs
        )