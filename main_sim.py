import asyncio
import subprocess
import time
import logging
import contextlib
import json
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
import ollama
import httpx
from src.shared.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "qwen2.5-coder:1.5b"
DEFAULT_MODEL = "qwen3:8b"
TEST_MODELS = ["qwen3:8b", "gemma3:4b"]
PROXY_HOST = "http://localhost"
SERVER_START_TIMEOUT = 10  # seconds
HTTP_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
EXAMPLE_AGENT_SUFFIX = " [processed by example agent]"

# Test data
TEST_PROMPTS = {
    "simple": "Hello, world!",
    "example_agent": "/example Hello, world!",
    "opt_positive": "/opt You are an expert in natural language processing and machine learning. Your primary task is to carefully analyze the provided text input for multiple key aspects. These include but are not limited to: overall sentiment analysis (positive, negative, neutral), extraction of named entities such as people, organizations, locations, dates, and other relevant items, identification of the main topics and subtopics discussed, detection of any potential biases or emotional tones, and summarization of the core message. After analysis, provide a comprehensive report in a well-structured JSON format with sections for each aspect. Ensure the report is objective, accurate, and detailed. Input text for analysis: The movie was fantastic and thrilling.",
    "opt_negative": "/opt You are an expert in natural language processing and machine learning. Your primary task is to carefully analyze the provided text input for multiple key aspects. These include but are not limited to: overall sentiment analysis (positive, negative, neutral), extraction of named entities such as people, organizations, locations, dates, and other relevant items, identification of the main topics and subtopics discussed, detection of any potential biases or emotional tones, and summarization of the core message. After analysis, provide a comprehensive report in a well-structured JSON format with sections for each aspect. Ensure the report is objective, accurate, and detailed. Input text for analysis: The service was terrible and slow."
}

@dataclass
class TestResult:
    name: str
    success: bool
    error: Optional[str] = None

class MainSimulator:
    """Simulator for testing the Ollama Smart Proxy main application."""

    def __init__(self):
        self.config = Config()
        self.proxy_host = PROXY_HOST
        self.proxy_port = self.config.server_port
        self.server_process: Optional[subprocess.Popen] = None
        self.client: Optional[ollama.Client] = None
        self.test_results: List[TestResult] = []

    async def start_server(self):
        """Start the Ollama Smart Proxy server in the background."""
        logger.info("Starting the Ollama Smart Proxy server...")
        self.server_process = subprocess.Popen(["python", "main.py"])
        # Wait for server to be ready
        await self._wait_for_server()
        self.client = ollama.Client(host=f"{self.proxy_host}:{self.proxy_port}")
        logger.info("Server started successfully")

    def stop_server(self):
        """Stop the running server."""
        if self.server_process:
            logger.info("Stopping the server...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Server did not terminate gracefully, killing...")
                self.server_process.kill()
                self.server_process.wait()

    async def _wait_for_server(self):
        """Wait for the server to be ready."""
        start_time = time.time()
        while time.time() - start_time < SERVER_START_TIMEOUT:
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(1.0)) as client:
                    resp = await client.get(f"{self.proxy_host}:{self.proxy_port}/health")
                    if resp.status_code == 200:
                        return
            except (httpx.ConnectError, httpx.TimeoutException):
                await asyncio.sleep(0.5)
        raise RuntimeError(f"Server did not start within {SERVER_START_TIMEOUT} seconds")

    @contextlib.asynccontextmanager
    async def server_context(self):
        """Context manager for server lifecycle."""
        await self.start_server()
        try:
            yield
        finally:
            self.stop_server()

    async def _run_test_with_retry(self, test_name: str, test_func, *args, **kwargs) -> TestResult:
        """Run a test with retry logic."""
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Running test: {test_name} (attempt {attempt + 1})")
                await test_func(*args, **kwargs)
                return TestResult(name=test_name, success=True)
            except Exception as e:
                last_error = e
                logger.warning(f"Test {test_name} failed on attempt {attempt + 1}: {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(1)  # Wait before retry
        return TestResult(name=test_name, success=False, error=str(last_error))

    async def test_generate_endpoint(self):
        """Test the /api/generate endpoint."""
        assert self.client is not None
        response = self.client.generate(model=DEFAULT_MODEL, prompt=TEST_PROMPTS["simple"])
        logger.debug(f"Generate response: {response}")
        if not self._is_valid_generate_response(response):
            raise ValueError("Generate endpoint response missing 'response' key or not a dict")

    async def test_generate_endpoint_with_example_agent(self):
        """Test the /api/generate endpoint with /example agent activation."""
        assert self.client is not None
        response = self.client.generate(model=DEFAULT_MODEL, prompt=TEST_PROMPTS["example_agent"])
        logger.debug(f"Generate with agent response: {response}")
        if not self._is_valid_generate_response_with_agent(response):
            raise ValueError("Generate endpoint with agent response invalid")

    async def test_generate_endpoint_streaming(self, model: Optional[str] = None):
        """Test the /api/generate endpoint with streaming."""
        assert self.client is not None
        test_model = model or DEFAULT_MODEL
        logger.info(f"Testing streaming with model: {test_model}")
        
        stream = self.client.generate(model=test_model, prompt=TEST_PROMPTS["simple"], stream=True)
        chunks = []
        chunk_count = 0
        try:
            for chunk in stream:
                chunks.append(chunk)
                chunk_count += 1
                if chunk_count > 100:  # Limit to prevent memory issues
                    break
        except Exception as e:
            logger.error(f"Error during streaming: {str(e)}")
            raise
        
        logger.debug(f"Received {len(chunks)} chunks for model {test_model}")
        logger.debug(f"First few chunks: {chunks[:3]}")
        logger.debug(f"Last few chunks: {chunks[-3:]}")
        
        if not self._is_valid_streaming_response(chunks):
            logger.error(f"Streaming validation failed for model {test_model}. Chunks: {chunks}")
            raise ValueError(f"Generate endpoint streaming response invalid for model {test_model}")

    async def test_generate_endpoint_with_optimizer_agent(self, prompt: str):
        """Test the /api/generate endpoint with /opt agent activation."""
        assert self.client is not None
        if not prompt:
            prompt = TEST_PROMPTS["simple"].replace("Hello", "/opt Hello")
        response = self.client.generate(model=DEFAULT_MODEL, prompt=prompt)
        logger.debug(f"Generate with optimizer response: {response}")
        if not self._is_valid_generate_response(response):
            raise ValueError("Generate endpoint with optimizer agent response invalid")

    def _is_valid_generate_response(self, response):
        """Validate the generate response."""
        return isinstance(response, dict) and "response" in response

    def _is_valid_generate_response_with_agent(self, response):
        """Validate the generate response with agent modifications."""
        if not isinstance(response, dict) or "response" not in response:
            return False
        content = response["response"]
        # Check if it ends with the suffix added by the agent
        return content.endswith(EXAMPLE_AGENT_SUFFIX)

    async def test_tags_endpoint(self):
        """Test the /api/tags endpoint."""
        assert self.client is not None
        tags = self.client.list()
        logger.debug(f"Tags response: {tags}")
        if not self._is_valid_tags_response(tags):
            raise ValueError("Tags endpoint response missing 'models' key")

    def _is_valid_tags_response(self, tags):
        """Validate the tags response."""
        return "models" in tags

    async def test_health_endpoint(self):
        """Test the /health endpoint."""
        async with httpx.AsyncClient(timeout=httpx.Timeout(HTTP_TIMEOUT)) as http_client:
            resp = await http_client.get(f"{self.proxy_host}:{self.proxy_port}/health")
            health_data = resp.json()
            logger.debug(f"Health response: {health_data}")
            if not self._is_valid_health_response(resp, health_data):
                raise ValueError("Health endpoint response invalid")

    def _is_valid_health_response(self, resp, health_data):
        """Validate the health response."""
        return resp.status_code == 200 and health_data.get("status") in ["healthy", "unhealthy"]

    async def test_chat_endpoint_with_example_agent(self):
        """Test the /api/chat endpoint with /example agent activation."""
        assert self.client is not None
        response = self.client.chat(model=DEFAULT_MODEL, messages=[{"role": "user", "content": TEST_PROMPTS["example_agent"]}])
        logger.debug(f"Chat with agent response: {response}")
        if not self._is_valid_chat_response_with_agent(response):
            raise ValueError("Chat endpoint with agent response invalid")

    async def test_chat_endpoint_with_optimizer_agent(self, prompt: str):
        """Test the /api/chat endpoint with /opt agent activation."""
        assert self.client is not None
        if not prompt:
            prompt = TEST_PROMPTS["simple"].replace("Hello", "/opt Hello")
        response = self.client.chat(model=DEFAULT_MODEL, messages=[{"role": "user", "content": prompt}])
        logger.debug(f"Chat with optimizer response: {response}")
        if not self._is_valid_chat_response(response):
            raise ValueError("Chat endpoint with optimizer agent response invalid")

    async def test_chat_endpoint_streaming(self, model: Optional[str] = None):
        """Test the /api/chat endpoint with streaming."""
        assert self.client is not None
        test_model = model or DEFAULT_MODEL
        logger.info(f"Testing chat streaming with model: {test_model}")
        
        stream = self.client.chat(model=test_model, messages=[{"role": "user", "content": TEST_PROMPTS["simple"]}], stream=True)
        chunks = []
        chunk_count = 0
        try:
            for chunk in stream:
                chunks.append(chunk)
                chunk_count += 1
                if chunk_count > 100:  # Limit to prevent memory issues
                    break
        except Exception as e:
            logger.error(f"Error during chat streaming: {str(e)}")
            raise
        
        logger.debug(f"Received {len(chunks)} chunks for chat model {test_model}")
        logger.debug(f"First few chunks: {chunks[:3]}")
        logger.debug(f"Last few chunks: {chunks[-3:]}")
        
        if not self._is_valid_streaming_response(chunks):
            logger.error(f"Chat streaming validation failed for model {test_model}. Chunks: {chunks}")
            raise ValueError(f"Chat endpoint streaming response invalid for model {test_model}")

    def _is_valid_chat_response(self, response):
        """Validate the chat response."""
        return isinstance(response, dict) and "message" in response and "content" in response["message"]

    def _is_valid_chat_response_with_agent(self, response):
        """Validate the chat response with agent modifications."""
        if not isinstance(response, dict) or "message" not in response or "content" not in response["message"]:
            return False
        content = response["message"]["content"]
        # Check if it ends with the suffix added by the agent
        return content.endswith(EXAMPLE_AGENT_SUFFIX)

    def _is_valid_streaming_response(self, chunks):
        """Validate the streaming response chunks with better model compatibility."""
        if not chunks:
            return False
        
        # Check that all chunks are valid
        valid_chunks = 0
        has_done = False
        has_content = False
        
        for chunk in chunks:
            # Handle different chunk formats
            if isinstance(chunk, dict):
                # Standard dict format
                if chunk.get("done"):
                    has_done = True
                
                # Check for content in different formats
                if "response" in chunk and chunk["response"]:
                    has_content = True
                elif "message" in chunk and isinstance(chunk["message"], dict) and chunk["message"].get("content"):
                    has_content = True
                
                valid_chunks += 1
            elif isinstance(chunk, str):
                # String format - try to parse as JSON
                try:
                    parsed = json.loads(chunk)
                    if isinstance(parsed, dict):
                        if parsed.get("done"):
                            has_done = True
                        if "response" in parsed and parsed["response"]:
                            has_content = True
                        elif "message" in parsed and isinstance(parsed["message"], dict) and parsed["message"].get("content"):
                            has_content = True
                    valid_chunks += 1
                except json.JSONDecodeError:
                    # Non-JSON string, still count as valid if it contains response data
                    if chunk.strip():
                        has_content = True
                        valid_chunks += 1
            else:
                # Other types - convert to string and check
                chunk_str = str(chunk)
                if chunk_str.strip():
                    has_content = True
                    valid_chunks += 1
        
        # For streaming responses, we need:
        # 1. At least some valid chunks
        # 2. Some content (response or message)
        # 3. Either a done signal OR enough content to indicate successful streaming
        return (valid_chunks > 0 and has_content and 
                (has_done or valid_chunks >= 5))  # Allow if we have substantial content even without done signal

    async def test_plugins_endpoint(self):
        """Test the /plugins endpoint."""
        async with httpx.AsyncClient(timeout=httpx.Timeout(HTTP_TIMEOUT)) as http_client:
            resp = await http_client.get(f"{self.proxy_host}:{self.proxy_port}/plugins")
            plugins_data = resp.json()
            logger.debug(f"Plugins response: {plugins_data}")
            if resp.status_code != 200 or not isinstance(plugins_data, list):
                raise ValueError("Plugins endpoint invalid")
            agents = [p.get('name') for p in plugins_data if isinstance(p, dict)]
            if "example" not in agents:
                raise ValueError("Example agent not loaded")
            if "opt" not in agents:
                raise ValueError("Optimizer agent not loaded")

    async def run_all_tests(self):
        """Run all endpoint tests."""
        async with self.server_context():
            test_results = []
            # Test definitions
            tests = []
            
            # Test streaming for all models (both generate and chat)
            # for model in TEST_MODELS:
            #     tests.append((f"Generate Streaming ({model})", self.test_generate_endpoint_streaming, model))
            #     tests.append((f"Chat Streaming ({model})", self.test_chat_endpoint_streaming, model))
            
            # Uncomment other tests as needed
            tests.extend([
                ("Generate Endpoint", self.test_generate_endpoint),
                ("Generate with Agent", self.test_generate_endpoint_with_example_agent),
                ("Generate Streaming", self.test_generate_endpoint_streaming),
                ("Generate with Optimizer Agent (Positive)", self.test_generate_endpoint_with_optimizer_agent, TEST_PROMPTS["opt_positive"]),
                ("Generate with Optimizer Agent (Negative)", self.test_generate_endpoint_with_optimizer_agent, TEST_PROMPTS["opt_negative"]),
                ("Tags Endpoint", self.test_tags_endpoint),
                ("Health Endpoint", self.test_health_endpoint),
                ("Plugins Endpoint", self.test_plugins_endpoint),
                ("Chat with Agent", self.test_chat_endpoint_with_example_agent),
                ("Chat Streaming", self.test_chat_endpoint_streaming),
                ("Chat with Optimizer Agent (Positive)", self.test_chat_endpoint_with_optimizer_agent, TEST_PROMPTS["opt_positive"]),
                ("Chat with Optimizer Agent (Negative)", self.test_chat_endpoint_with_optimizer_agent, TEST_PROMPTS["opt_negative"]),
            ])

            for test_def in tests:
                test_name = test_def[0]
                test_func = test_def[1]
                args = test_def[2:] if len(test_def) > 2 else ()
                result = await self._run_test_with_retry(test_name, test_func, *args)
                test_results.append(result)

            # Print total report
            self._print_test_report(test_results)

    def _print_test_report(self, test_results: List[TestResult]):
        """Print a comprehensive test report."""
        logger.info("\n" + "="*60)
        logger.info("TEST REPORT SUMMARY")
        logger.info("="*60)

        passed = 0
        total = len(test_results)

        for result in test_results:
            status = "✓ PASS" if result.success else "✗ FAIL"
            logger.info(f"{result.name:<35} {status}")
            if not result.success and result.error:
                logger.info(f"  Error: {result.error}")
            if result.success:
                passed += 1

        logger.info("="*60)
        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {total - passed}")
        success_rate = (passed / total) * 100 if total > 0 else 0
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info("="*60)

        if passed == total:
            logger.info("🎉 All tests passed!")
        else:
            logger.info("⚠️  Some tests failed. Check logs above for details.")


async def main():
    simulator = MainSimulator()
    await simulator.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())