"""Base class for agent chains in the Ollama Smart Proxy."""

import re
import httpx
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set, Optional

from pydantic import BaseModel
from fastapi.responses import StreamingResponse

from shared.config import Config
from shared.logging import LoggingManager
from src.const import RESPONSE_FIELD, MODEL_FIELD, STREAM_FIELD, AGENTS_FIELD


class BaseChain(ABC):
    """Base class for handling request processing and Ollama forwarding."""

    # Pre-compile regex pattern at class level
    _AGENT_COMMAND_PATTERN = re.compile(r'^\s*/(\w+)\s*')

    def __init__(self, registry):
        self.registry = registry
        self.logger = LoggingManager.get_logger(__name__)
        self._model_cache: Optional[Dict[str, float]] = None
        self.config = Config()
        self._cache_ttl = self.config.model_cache_ttl

    def _parse_slash_commands(self, content: str) -> tuple[str, Set[str]]:
        """Parse slash commands from content.

        Args:
            content: The content to parse.

        Returns:
            Tuple of (cleaned_content, set_of_agent_names).
        """
        # Parse leading slash commands
        agents = set()
        pos = 0
        while True:
            match = self._AGENT_COMMAND_PATTERN.match(content[pos:])
            if match:
                agents.add(match.group(1))
                pos += match.end()
            else:
                break
        cleaned_content = content[pos:].strip()
        return cleaned_content, agents

    async def _execute_agent_chain_on_request(
        self, agents: List[str], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute on_request hooks for agents in sequence.

        Args:
            agents: List of agent names to execute.
            context: Request context to modify.

        Returns:
            Modified context after all agents have processed it.
        """
        for agent_name in agents:
            agent = self.registry.get_agent(agent_name)
            if agent:
                context = await agent.on_request(context)

        return context

    async def _execute_agent_chain_on_response(
        self, agents: List[str], request_context: Dict[str, Any], response_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute on_response hooks for agents in reverse sequence.

        Args:
            agents: List of agent names to execute (in reverse order).
            request_context: Original request context.
            response_context: Response context to modify.

        Returns:
            Modified context after all agents have processed it.
        """
        response_key = self.get_response_key()
        content_path = self.get_content_path()

        response = response_context[response_key]
        content = self._get_nested_value(response, content_path)
        self.logger.debug(f"Before agent chain response processing: {content[:200]}{'...' if len(content) > 200 else ''}")

        # Process response through each agent in reverse order
        for agent_name in agents:
            agent = self.registry.get_agent(agent_name)
            if agent:
                response = await agent.on_response(request_context, response)

        # Update the context with the modified response
        response_context[response_key] = response
        content = self._get_nested_value(response, content_path)
        self.logger.debug(f"After agent chain response processing: {content[:200]}{'...' if len(content) > 200 else ''}")
        return response_context

    def _get_nested_value(self, obj: Dict[str, Any], path: List[str]) -> str:
        """Get nested value from dict using path."""
        for key in path:
            if isinstance(obj, dict):
                obj = obj.get(key, {})
            else:
                return ""
        return obj if isinstance(obj, str) else ""

    @abstractmethod
    def get_ollama_endpoint(self) -> str:
        """Return the Ollama API endpoint path."""
        pass

    @abstractmethod
    def prepare_context(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare the request context from raw request data."""
        pass

    @abstractmethod
    def get_content_for_agent_parsing(self, request: Dict[str, Any]) -> str:
        """Get the content string to parse for agent commands."""
        pass

    @abstractmethod
    def update_content_in_context(self, context: Dict[str, Any], cleaned_content: str):
        """Update the content in the context after cleaning agent commands."""
        pass

    @abstractmethod
    def build_ollama_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build the request dict to send to Ollama."""
        pass

    @abstractmethod
    def create_response_context(self, response_data: Dict[str, Any], agents: List[str]) -> Dict[str, Any]:
        """Create the response context from Ollama response data."""
        pass

    @abstractmethod
    def get_response_key(self) -> str:
        """Get the key for the response object in response_context."""
        pass

    @abstractmethod
    def get_content_path(self) -> List[str]:
        """Get the path to the content string in the response object."""
        pass

    @abstractmethod
    def get_final_key(self) -> str:
        """Get the key for the final response in response_context."""
        pass

    async def process_request(self, request: Dict[str, Any]) -> Any:
        """Process a request and forward to Ollama.

        Args:
            request: The parsed request dict.

        Returns:
            The response from Ollama.
        """
        try:
            # Prepare context
            context = self.prepare_context(request)

            # Get content for parsing
            content = self.get_content_for_agent_parsing(request)
            cleaned_content, agent_names = self._parse_slash_commands(content)
            self.update_content_in_context(context, cleaned_content)
            agents_to_execute = list(agent_names)
            context[AGENTS_FIELD] = agents_to_execute

            if agents_to_execute:
                self.logger.info(f"Activating agents: {agents_to_execute}")

            # Execute agent chain on request
            context = await self._execute_agent_chain_on_request(agents_to_execute, context)

            # Forward to Ollama
            self.logger.debug(f"Forwarding request to Ollama for model: {context.get(MODEL_FIELD)}")
            url = f"{self.config.ollama_host}:{self.config.ollama_port}{self.get_ollama_endpoint()}"
            request_dict = self.build_ollama_request(context)
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=request_dict)

            if context.get(STREAM_FIELD, False):
                self.logger.info(f"Request processed successfully for model: {context.get(MODEL_FIELD)} (streaming)")
                return StreamingResponse(
                    response.aiter_bytes(),
                    status_code=response.status_code,
                    headers=response.headers
                )
            else:
                # Parse the JSON response
                response_data = response.json()

                # Create response context
                response_context = self.create_response_context(response_data, agents_to_execute)

                # Execute agent chain on response
                response_context = await self._execute_agent_chain_on_response(
                    agents_to_execute, context, response_context
                )

                self.logger.info(f"Request processed successfully for model: {context.get(MODEL_FIELD)}")
                return response_context[self.get_final_key()]
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}", stack_info=True)
            raise
