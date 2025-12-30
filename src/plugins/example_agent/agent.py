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

    async def on_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the response context after receiving from Ollama.

        Adds a suffix to the response content.

        Args:
            context: Response context dictionary containing response data.

        Returns:
            Modified context dictionary.
        """
        if "message" in context and "content" in context["message"]:
            # Chat response
            content = context["message"]["content"]
            context["message"]["content"] = f"{content} [processed by example agent]"
        elif "response" in context:
            # Generate response
            content = context["response"]
            context["response"] = f"{content} [processed by example agent]"

        return context