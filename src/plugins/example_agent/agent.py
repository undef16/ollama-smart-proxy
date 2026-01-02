"""Example agent that demonstrates basic request/response modification."""

from typing import Any, Dict

from src.shared.base_agent import BaseAgent


class ExampleAgent(BaseAgent):
    """Example agent that adds a prefix to user messages and suffixes to responses."""

    @property
    def name(self) -> str:
        """The name of the agent, used for slash command activation."""
        return "example"

    async def on_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the request context before sending to Ollama.

        Adds a prefix to the last user message.

        Args:
            context: Request context dictionary containing request data.

        Returns:
            Modified context dictionary.
        """
        messages = context.get("messages", [])
        if messages:
            # Modify the last user message
            last_message = messages[-1]
            if last_message["role"] == "user":
                content = last_message["content"]
                last_message["content"] = f"[Example Agent] {content}"

        return context

    async def on_response(self, request: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
        """Process the response after receiving from Ollama.

        Adds a suffix to the response content.

        Args:
            request: Request context dictionary containing request data.
            response: Response dictionary from Ollama.

        Returns:
            Modified response dictionary.
        """
        if "message" in response and "content" in response["message"]:
            # Chat response
            content = response["message"]["content"]
            response["message"]["content"] = f"{content} [processed by example agent]"
        elif "response" in response:
            # Generate response
            content = response["response"]
            response["response"] = f"{content} [processed by example agent]"

        return response