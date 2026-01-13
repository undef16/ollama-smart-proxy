import json
import logging
import re
from typing import Any, Dict, Optional

from src.shared.base_agent import BaseAgent
from src.plugins.rag.infrastructure.adapters.lightrag_adapter import LightRAGAdapter
from src.plugins.rag.infrastructure.adapters.searxng_adapter import SearxNGAdapter
from src.plugins.rag.infrastructure.config import ConfigurationManager
from src.plugins.rag.infrastructure.langgraph.crag_graph import CRAGGraph
from src.plugins.rag.infrastructure.logging import RagError

logger = logging.getLogger(__name__)


class RagAgent(BaseAgent):
    """
    RAG (Retrieval-Augmented Generation) Agent for the Ollama Smart Proxy.

    This agent implements the Corrective RAG (CRAG) pattern using LangGraph as the state machine,
    LightRAG for knowledge graph and vector search, Neo4j for graph storage, PostgreSQL for vector
    and key-value storage, and SearxNG for external web search fallback.

    The agent handles /rag commands by retrieving relevant context from local knowledge base,
    falling back to web search if relevance is below threshold (0.6), and injecting the context
    into the prompt before forwarding to Ollama.

    This is the main entry point for the RAG plugin, structured according to hexagonal architecture.
    """

    def __init__(self):
        """Initialize the RAG agent with its dependencies."""
        self._crag_graph: Optional[CRAGGraph] = None
        self._initialized = False

    @property
    def name(self) -> str:
        """The name of the agent, used for /rag command activation."""
        return "rag"

    def _ensure_initialized(self) -> None:
        """Ensure the agent is properly initialized with its dependencies."""
        if self._initialized:
            return

        try:
            logger.info("Initializing RAG agent dependencies")

            # Initialize adapters
            rag_repository = LightRAGAdapter.create_from_config()
            search_service = SearxNGAdapter.create_from_config()

            # Initialize CRAG graph
            self._crag_graph = CRAGGraph(rag_repository, search_service)
            self.config = ConfigurationManager.get_config()

            self._initialized = True
            logger.info("RAG agent initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize RAG agent: {e}")
            raise RagError(f"RAG agent initialization failed: {e}")

    def _extract_query_from_prompt(self, request: Dict[str, Any]) -> Optional[str]:
        """Extract the actual query from the request, removing the /rag command.

        Handles both chat messages and generate prompts, similar to optimizer agent.

        Args:
            request: Request dictionary containing prompt or messages.

        Returns:
            The query text without the /rag command, or None if no /rag command found.
        """
        # Handle chat messages
        if "messages" in request:
            messages = request["messages"]
            for message in reversed(messages):
                if message.get("role") == "user":
                    return message.get("content", "")
            return json.dumps(messages)

        # Handle generate prompt
        elif "prompt" in request:
            prompt = request["prompt"]
            return prompt

        return None  # No /rag command found

    def _inject_context_into_request(self, request: Dict[str, Any], context_result: str) -> Dict[str, Any]:
        """Inject the retrieved context into the request, handling both chat and generate formats.

        Args:
            request: The original request dictionary.
            context_result: The retrieved context to inject w user request or question.

        Returns:
            The modified request dictionary with context injected.
        """
        if not request:
            logger.debug("No context to inject, returning original request")
            return request

        # Handle chat messages by finding the last user message and replacing its content
        if "messages" in request:
            messages = request["messages"]
            # Find the last user message to replace with the enriched context
            for message in reversed(messages):
                if message.get("role") == "user":
                    message["content"] = context_result
                    break

        elif "prompt" in request:
            request["prompt"] = context_result

        return request

    async def on_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the request context for RAG retrieval and injection.

        This method activates the LangGraph CRAG cycle: retrieves from LightRAG (Neo4j/PostgreSQL),
        grades relevance, performs web search via SearxNG if needed, and injects context into the prompt.

        Handles both chat messages and generate prompts, similar to optimizer agent.

        Args:
            context: Request context dictionary containing request data.

        Returns:
            Modified context dictionary with injected RAG context.
        """
        try:
            # Ensure agent is initialized
            self._ensure_initialized()

            if self._crag_graph is None:
                raise RagError("CRAG graph not initialized")

            new_request = request.copy()
            # Extract query from context (handles both chat messages and generate prompts)
            query_text = self._extract_query_from_prompt(new_request)

            # Run CRAG pipeline
            context_result = await self._crag_graph.run(query_text)

            # Format the system context using the template from config
            system_context = self.config.system_context.format(context=context_result, query=query_text)

            # Inject the formatted system context into the request
            new_request = self._inject_context_into_request(new_request, system_context)

            return new_request

        except Exception as e:
            logger.error(f"Error processing RAG request: {e}", stack_info=True)
            # Return original context on error to avoid breaking the flow
            return request

    async def on_response(self, request: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the response after receiving from Ollama.

        For RAG, this method currently does nothing as the response is passed through unchanged.

        Args:
            request: Request context dictionary containing request data.
            response: Response dictionary from Ollama.

        Returns:
            Unmodified response dictionary.
        """
        # No modifications needed for RAG on response
        return response