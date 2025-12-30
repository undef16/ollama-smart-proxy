import asyncio
import subprocess
import time
from typing import Optional
import ollama
import httpx
from src.shared.config import Config


class MainSimulator:
    """Simulator for testing the Ollama Smart Proxy main application."""

    def __init__(self):
        self.config = Config()
        self.proxy_host = "localhost"  # since server_host is 0.0.0.0, use localhost for client
        self.proxy_port = self.config.server_port
        self.server_process: Optional[subprocess.Popen] = None
        self.client: Optional[ollama.Client] = None

    def start_server(self):
        """Start the Ollama Smart Proxy server in the background."""
        print("Starting the Ollama Smart Proxy server...")
        self.server_process = subprocess.Popen(["python", "main.py"])
        time.sleep(3)  # Wait for server to start
        self.client = ollama.Client(host=f"http://{self.proxy_host}:{self.proxy_port}")

    def stop_server(self):
        """Stop the running server."""
        if self.server_process:
            print("Stopping the server...")
            self.server_process.terminate()
            self.server_process.wait()

    async def test_generate_endpoint(self):
        """Test the /api/generate endpoint."""
        print("Testing /api/generate...")
        try:
            response = self.client.generate(model="qwen2.5-coder:1.5b", prompt="Hello, world!")
            print("Generate response:", response)
            # Basic validation
            if self._is_valid_generate_response(response):
                print("✓ Generate endpoint returned proper response")
            else:
                print("✗ Generate endpoint response missing 'response' key or not a dict")
        except Exception as e:
            print(f"✗ Generate endpoint failed: {e}")

    def _is_valid_generate_response(self, response):
        """Validate the generate response."""
        return isinstance(response, dict) and "response" in response

    async def test_tags_endpoint(self):
        """Test the /api/tags endpoint."""
        print("Testing /api/tags...")
        try:
            tags = self.client.list()
            print("Tags response:", tags)
            # Basic validation
            if self._is_valid_tags_response(tags):
                print("✓ Tags endpoint returned proper response")
            else:
                print("✗ Tags endpoint response missing 'models' key")
        except Exception as e:
            print(f"✗ Tags endpoint failed: {e}")

    def _is_valid_tags_response(self, tags):
        """Validate the tags response."""
        return "models" in tags

    async def test_health_endpoint(self):
        """Test the /health endpoint."""
        print("Testing /health...")
        try:
            async with httpx.AsyncClient() as http_client:
                resp = await http_client.get(f"http://{self.proxy_host}:{self.proxy_port}/health")
                health_data = resp.json()
                print("Health response:", health_data)
                # Basic validation
                if self._is_valid_health_response(resp, health_data):
                    print("✓ Health endpoint returned proper response")
                else:
                    print("✗ Health endpoint response invalid")
        except Exception as e:
            print(f"✗ Health endpoint failed: {e}")

    def _is_valid_health_response(self, resp, health_data):
        """Validate the health response."""
        return resp.status_code == 200 and health_data.get("status") in ["healthy", "unhealthy"]

    async def test_chat_endpoint_with_example_agent(self):
        """Test the /api/chat endpoint with /example agent activation."""
        print("Testing /api/chat with /example agent...")
        try:
            response = self.client.chat(model="qwen2.5-coder:1.5b", messages=[{"role": "user", "content": "/example Hello, world!"}])
            print("Chat response:", response)
            # Basic validation
            if self._is_valid_chat_response_with_agent(response):
                print("✓ Chat endpoint with agent returned proper response")
            else:
                print("✗ Chat endpoint with agent response invalid")
        except Exception as e:
            print(f"✗ Chat endpoint with agent failed: {e}")

    def _is_valid_chat_response_with_agent(self, response):
        """Validate the chat response with agent modifications."""
        if not isinstance(response, dict) or "message" not in response or "content" not in response["message"]:
            return False
        content = response["message"]["content"]
        # Check if it ends with the suffix added by the agent
        return content.endswith(" [processed by example agent]")

    async def test_plugins_endpoint(self):
        """Test the /plugins endpoint."""
        print("Testing /plugins...")
        try:
            async with httpx.AsyncClient() as http_client:
                resp = await http_client.get(f"http://{self.proxy_host}:{self.proxy_port}/plugins")
                plugins_data = resp.json()
                print("Plugins response:", plugins_data)
                if resp.status_code == 200 and isinstance(plugins_data, list):
                    agents = [p.get('name') for p in plugins_data if isinstance(p, dict)]
                    if "example" in agents:
                        print("✓ Example agent is loaded")
                    else:
                        print("✗ Example agent not loaded")
                else:
                    print("✗ Plugins endpoint invalid")
        except Exception as e:
            print(f"✗ Plugins endpoint failed: {e}")

    async def run_all_tests(self):
        """Run all endpoint tests."""
        self.start_server()
        try:
            await self.test_generate_endpoint()
            await self.test_tags_endpoint()
            await self.test_health_endpoint()
            await self.test_plugins_endpoint()
            await self.test_chat_endpoint_with_example_agent()
        finally:
            self.stop_server()


async def main():
    simulator = MainSimulator()
    await simulator.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())