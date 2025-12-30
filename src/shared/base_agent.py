from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):
    """Base class for all agents in the Ollama Smart Proxy.

    Agents can modify requests and responses through the agent chain.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the agent, used for slash command activation."""
        pass

    @abstractmethod
    async def on_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the request context before sending to Ollama.

        Args:
            context: Request context dictionary containing request data.

        Returns:
            Modified context dictionary.
        """
        pass

    @abstractmethod
    async def on_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the response context after receiving from Ollama.

        Args:
            context: Response context dictionary containing response data.

        Returns:
            Modified context dictionary.
        """
        pass