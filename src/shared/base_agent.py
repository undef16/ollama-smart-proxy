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
    async def on_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process the request context before sending to Ollama.

        Args:
            request: Request context dictionary containing request data.

        Returns:
            Modified request dictionary.
        """
        pass

    @abstractmethod
    async def on_response(self, request: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
        """Process the response after receiving from Ollama.

        Args:
            request: Request context dictionary.
            response: Response dictionary from Ollama.

        Returns:
            Modified response dictionary.
        """
        pass
