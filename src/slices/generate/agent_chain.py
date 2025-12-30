"""Generate processing logic for the Ollama Smart Proxy."""

import re
import time
from typing import Any, Dict, List, Set, Optional

from pydantic import BaseModel

from shared.config import Config
from shared.logging import LoggingManager


class GenerateRequest(BaseModel):
    """OpenAI-compatible generate request model."""

    model: str
    prompt: str
    stream: bool = False


class GenerateChain:
    """Handles generate request processing and Ollama forwarding."""

    def __init__(self, registry, ollama_client):
        self.registry = registry
        self.ollama_client = ollama_client
        self.logger = LoggingManager.get_logger(__name__)
        self._model_cache: Optional[Dict[str, float]] = None
        config = Config()
        self._cache_ttl = config.model_cache_ttl

    def _parse_slash_commands(self, content: str) -> tuple[str, Set[str]]:
        """Parse slash commands from prompt content.

        Args:
            content: The prompt content to parse.

        Returns:
            Tuple of (cleaned_content, set_of_agent_names).
        """
        # Find all /agent commands
        config = Config()
        agent_pattern = config.agent_command_pattern
        agents = set(re.findall(agent_pattern, content))

        # Remove slash commands from content
        cleaned_content = re.sub(agent_pattern, '', content).strip()

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
        self, agents: List[str], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute on_response hooks for agents in reverse sequence.

        Args:
            agents: List of agent names to execute (in reverse order).
            context: Response context to modify.

        Returns:
            Modified context after all agents have processed it.
        """
        # Get the actual response from the context
        response = context["response"]
        self.logger.info(f"Before agent chain response processing: {response.get('response', 'NO RESPONSE')}")

        # Process response through each agent
        for agent_name in reversed(agents):
            agent = self.registry.get_agent(agent_name)
            if agent:
                self.logger.info(f"Processing response through agent: {agent_name}")
                self.logger.info(f"Response before agent {agent_name}: {response.get('response', 'NO RESPONSE')}")
                response = await agent.on_response(response)
                self.logger.info(f"Response after agent {agent_name}: {response.get('response', 'NO RESPONSE')}")

        # Update the context with the modified response
        context["response"] = response
        self.logger.info(f"After agent chain response processing: {response.get('response', 'NO RESPONSE')}")
        return context

    async def process_generate_request(self, generate_request: GenerateRequest) -> Any:
        """Process a generate request and forward to Ollama.

        Args:
            generate_request: The parsed generate request.

        Returns:
            The response from Ollama.
        """
        try:
            # Extract model and prompt
            model = generate_request.model
            prompt = generate_request.prompt

            self.logger.info(f"Processing generate request for model: {model}")

            # Parse slash commands from the prompt
            agents_to_execute = []
            cleaned_prompt, agent_names = self._parse_slash_commands(prompt)
            self.logger.info(f"Parsed agent names: {agent_names}, cleaned prompt: {cleaned_prompt}")
            agents_to_execute = list(agent_names)

            if agents_to_execute:
                self.logger.info(f"Activating agents: {agents_to_execute}")

            # Create request context
            context = {
                "model": model,
                "prompt": cleaned_prompt,
                "stream": generate_request.stream,
                "agents": agents_to_execute
            }

            # Execute agent chain on request
            context = await self._execute_agent_chain_on_request(agents_to_execute, context)

            # Ensure model is loaded (lazy loading)
            # await self._ensure_model_loaded(context["model"])

            # Forward to Ollama
            self.logger.debug(f"Forwarding request to Ollama for model: {context['model']}")
            response = await self.ollama_client.generate(
                model=context["model"],
                prompt=context["prompt"],
                stream=context["stream"]
            )

            if context["stream"]:
                self.logger.info(f"Generate request processed successfully for model: {model} (streaming)")
                return response
            else:
                # Create response context
                response_context = {
                    "response": response,
                    "agents": agents_to_execute
                }

                # Execute agent chain on response
                self.logger.info(f"Before agent response processing: {response_context['response'].get('response', 'NO RESPONSE')}")
                response_context = await self._execute_agent_chain_on_response(
                    agents_to_execute, response_context
                )
                self.logger.info(f"After agent response processing: {response_context['response'].get('response', 'NO RESPONSE')}")

                self.logger.info(f"Generate request processed successfully for model: {model}")
                return response_context["response"]
        except Exception as e:
            self.logger.error(f"Error processing generate request: {str(e)}")
            raise

    async def _ensure_model_loaded(self, model: str) -> None:
        """Ensure the specified model is loaded, pulling it if necessary.

        Args:
            model: The model name to ensure is loaded.
        """
        try:
            # Check cache first
            current_time = time.time()
            if (self._model_cache is None or
                current_time - self._model_cache.get('_timestamp', 0) > self._cache_ttl):
                # Cache expired or not initialized, refresh
                self.logger.debug("Refreshing model cache")
                available_models = await self.ollama_client.list()
                model_names = [m.get('name') for m in available_models.get('models', [])]
                self._model_cache = {name: current_time for name in model_names}
                self._model_cache['_timestamp'] = current_time
            else:
                model_names = list(self._model_cache.keys())
                model_names.remove('_timestamp')  # Remove timestamp from model list

            if model not in model_names:
                # Model not loaded, pull it
                self.logger.info(f"Model {model} not found, pulling from Ollama")
                await self.ollama_client.pull(model)
                self.logger.info(f"Successfully pulled model: {model}")
                # Update cache
                self._model_cache[model] = current_time
            else:
                self.logger.debug(f"Model {model} is already available")
        except Exception as e:
            self.logger.error(f"Error ensuring model {model} is loaded: {str(e)}")
            raise