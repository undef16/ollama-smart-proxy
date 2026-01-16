import asyncio
import subprocess
import time
import logging
import contextlib
import json
from typing import Optional, List
from dataclasses import dataclass
import ollama
import httpx
from src.shared.config import Config
from src.const import (
    DEFAULT_TEST_MODEL, ROLE_FIELD, SERVER_START_TIMEOUT_SEC,
    HTTP_TIMEOUT_SEC, EXAMPLE_AGENT_SUFFIX_STR, TEST_PROMPT_OPT_POSITIVE,
    TEST_PROMPT_SIMPLE, TEST_PROMPT_WITH_AGENT, TEST_PROMPT_OPT_NEGATIVE,
    TEST_PROMPT_RAG, HEALTH_STATUS_HEALTHY, HEALTH_STATUS_UNHEALTHY,
    MESSAGE_FIELD, CONTENT_FIELD, RESPONSE_FIELD, DONE_FIELD, USER_ROLE
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Suppress noisy library logs
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Constants are imported from src.const

# Test data constants are imported from src.const

@dataclass
class TestResult:
    name: str
    success: bool
    error: Optional[str] = None

class MainSimulator:
    """Simulator for testing the Ollama Smart Proxy main application."""

    def __init__(self):
        self.config = Config()
        self.proxy_host = self.config.proxy_host_url
        self.proxy_port = self.config.server_port
        self.server_process: Optional[subprocess.Popen] = None
        self.client: ollama.Client
        self.test_results: List[TestResult] = []

    async def start_server(self):
        """Start the Ollama Smart Proxy server in the background."""
        logger.info("Starting the Ollama Smart Proxy server...")

        self.server_process = subprocess.Popen(["python", "main.py"])
        # # Wait for server to be ready
        await self._wait_for_server()
        
        self.client = ollama.Client(host=f"{self.proxy_host}:{self.proxy_port}")
               
        # self.client = ollama.Client(host=f"{self.proxy_host}:11434")
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
        while time.time() - start_time < SERVER_START_TIMEOUT_SEC:
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(1.0)) as client:
                    resp = await client.get(f"{self.proxy_host}:{self.proxy_port}/health")
                    if resp.status_code == 200:
                        return
            except (httpx.ConnectError, httpx.TimeoutException):
                await asyncio.sleep(0.5)
         

    @contextlib.asynccontextmanager
    async def server_context(self):
        """Context manager for server lifecycle."""
        await self.start_server()
        try:
            yield
        finally:
            self.stop_server()

    async def _run_single_test(self, test_name: str, test_func, *args, **kwargs) -> TestResult:
        """Run a test once without retry logic."""
        try:
            logger.info(f"Running test: {test_name}")
            await test_func(*args, **kwargs)
            return TestResult(name=test_name, success=True)
        except Exception as e:
            logger.warning(f"Test {test_name} failed: {e}")
            return TestResult(name=test_name, success=False, error=str(e))

    async def test_generate_endpoint(self):
        """Test the /api/generate endpoint."""
        
        response = self.client.generate(model=DEFAULT_TEST_MODEL, prompt=TEST_PROMPT_SIMPLE)
        logger.info(f"Generate response: {response}")
        if not self._is_valid_generate_response(response):
            raise ValueError("Generate endpoint response missing 'response' key or not a dict")

    async def test_generate_endpoint_with_example_agent(self):
        """Test the /api/generate endpoint with /example agent activation."""
        
        response = self.client.generate(model=DEFAULT_TEST_MODEL, prompt=TEST_PROMPT_WITH_AGENT)
        logger.debug(f"Generate with agent response: {response}")
        if not self._is_valid_generate_response_with_agent(response):
            raise ValueError("Generate endpoint with agent response invalid")

    async def test_generate_endpoint_streaming(self, model: Optional[str] = None):
        """Test the /api/generate endpoint with streaming."""
        
        test_model = model or DEFAULT_TEST_MODEL
        logger.info(f"Testing streaming with model: {test_model}")
        
        stream = self.client.generate(model=test_model, prompt=TEST_PROMPT_SIMPLE, stream=True)
        result = ''
        chunk_count = 0
        try:
            for chunk in stream:
                result += chunk.response
                logger.info(f'Chunk: {chunk.response}')
                chunk_count += 1
                if chunk_count > 100:  # Limit to prevent memory issues
                    break
        except Exception as e:
            logger.error(f"Fail generate endpoint streaming response {e}", stack_info=True)    
            raise ValueError(f"Generate endpoint streaming response invalid for model {test_model}")
        
        logger.info(f"Generate endpoint streaming response {result}")    

    async def test_generate_endpoint_with_optimizer_agent(self, prompt: str):
        """Test the /api/generate endpoint with /opt agent activation."""
        
        if not prompt:
            prompt = TEST_PROMPT_SIMPLE.replace("Hello", "/opt Hello")
        response = self.client.generate(model=DEFAULT_TEST_MODEL, prompt=prompt)
        logger.debug(f"Generate with optimizer response: {response}")
        if not self._is_valid_generate_response(response):
            raise ValueError("Generate endpoint with optimizer agent response invalid")

    async def test_generate_endpoint_with_rag_agent(self):
        """Test the /api/generate endpoint with /rag agent activation."""
        
        response = self.client.generate(model=DEFAULT_TEST_MODEL, prompt=TEST_PROMPT_RAG)
        logger.debug(f"Generate with RAG response: {response}")
        if not self._is_valid_generate_response(response):
            raise ValueError("Generate endpoint with RAG agent response invalid")

    def _is_valid_generate_response(self, response):
        """Validate the generate response."""
        return RESPONSE_FIELD in response

    def _is_valid_generate_response_with_agent(self, response):
        """Validate the generate response with agent modifications."""
        content = response[RESPONSE_FIELD]
        # Check if it ends with the suffix added by the agent
        return content.endswith(EXAMPLE_AGENT_SUFFIX_STR)

    async def test_tags_endpoint(self):
        """Test the /api/tags endpoint."""
        
        tags = self.client.list()
        logger.debug(f"Tags response: {tags}")
        if not self._is_valid_tags_response(tags):
            raise ValueError("Tags endpoint response missing 'models' key")

    def _is_valid_tags_response(self, tags):
        """Validate the tags response."""
        return "models" in tags

    async def test_health_endpoint(self):
        """Test the /health endpoint."""
        async with httpx.AsyncClient(timeout=httpx.Timeout(HTTP_TIMEOUT_SEC)) as http_client:
            resp = await http_client.get(f"{self.proxy_host}:{self.proxy_port}/health")
            health_data = resp.json()
            logger.debug(f"Health response: {health_data}")
            if not self._is_valid_health_response(resp, health_data):
                raise ValueError("Health endpoint response invalid")

    def _is_valid_health_response(self, resp, health_data):
        """Validate the health response."""
        return resp.status_code == 200 and health_data.get("status") in [HEALTH_STATUS_HEALTHY, HEALTH_STATUS_UNHEALTHY]

    async def test_chat_endpoint_with_example_agent(self):
        """Test the /api/chat endpoint with /example agent activation."""
        
        response = self.client.chat(model=DEFAULT_TEST_MODEL, messages=[{ROLE_FIELD: USER_ROLE, CONTENT_FIELD: TEST_PROMPT_WITH_AGENT}])
        logger.debug(f"Chat with agent response: {response}")
        if not self._is_valid_chat_response_with_agent(response):
            raise ValueError("Chat endpoint with agent response invalid")

    async def test_chat_endpoint_with_optimizer_agent(self, prompt: str):
        """Test the /api/chat endpoint with /opt agent activation."""
        
        if not prompt:
            prompt = TEST_PROMPT_SIMPLE.replace("Hello", "/opt Hello")
        response = self.client.chat(model=DEFAULT_TEST_MODEL, messages=[{ROLE_FIELD: USER_ROLE, CONTENT_FIELD: prompt}])
        logger.debug(f"Chat with optimizer response: {response}")
        if not self._is_valid_chat_response(response):
            raise ValueError("Chat endpoint with optimizer agent response invalid")

    async def test_chat_endpoint_with_rag_agent(self):
        """Test the /api/chat endpoint with /rag agent activation."""
        
        response = self.client.chat(model=DEFAULT_TEST_MODEL, messages=[{ROLE_FIELD: USER_ROLE, CONTENT_FIELD: TEST_PROMPT_RAG}], stream=False)
        logger.info(f"Chat with RAG response: {response}")
        if not self._is_valid_chat_response(response):
            raise ValueError("Chat endpoint with RAG agent response invalid")

    async def test_generate_endpoint_with_moa_agent(self):
        """Test the /api/generate endpoint with /moa agent activation."""
        
        prompt = "/moa " + TEST_PROMPT_SIMPLE
        response = self.client.generate(model=DEFAULT_TEST_MODEL, prompt=prompt)
        logger.info(f"Generate with MoA response: {response}")
        if not self._is_valid_moa_response(response):
            raise ValueError("Generate endpoint with MoA agent response invalid")

    async def test_chat_endpoint_with_moa_agent(self):
        """Test the /api/chat endpoint with /moa agent activation."""
        
        messages = [{ROLE_FIELD: USER_ROLE, CONTENT_FIELD: "/moa " + TEST_PROMPT_SIMPLE}]
        response = self.client.chat(model=DEFAULT_TEST_MODEL, messages=messages, stream=False)
        logger.info(f"Chat with MoA response: {response}")
        if not self._is_valid_moa_response(response):
            raise ValueError("Chat endpoint with MoA agent response invalid")

    async def test_chat_endpoint_streaming(self, model: Optional[str] = None):
        """Test the /api/chat endpoint with streaming."""
        
        test_model = model or DEFAULT_TEST_MODEL
        logger.info(f"Testing chat streaming with model: {test_model}")
        
        stream = self.client.chat(model=test_model, messages=[{ROLE_FIELD: USER_ROLE, CONTENT_FIELD: TEST_PROMPT_SIMPLE}], stream=True)
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
        # Handle both dict and Pydantic model responses from ollama client
        if hasattr(response, 'model_dump'):
            # Pydantic model - convert to dict
            response = response.model_dump()
        
        if not isinstance(response, dict):
            return False
            
        return MESSAGE_FIELD in response and CONTENT_FIELD in response.get(MESSAGE_FIELD, {})

    def _is_valid_chat_response_with_agent(self, response):
        """Validate the chat response with agent modifications."""
        if CONTENT_FIELD not in response[MESSAGE_FIELD]:
            return False
        content = response[MESSAGE_FIELD][CONTENT_FIELD]
        # Check if it ends with the suffix added by the agent
        return content.endswith(EXAMPLE_AGENT_SUFFIX_STR)

    def _is_valid_moa_response(self, response):
        """Validate the MoA response."""
        if isinstance(response, ollama.GenerateResponse):
            if RESPONSE_FIELD in response:
                # In case it falls back to generate format
                return bool(response[RESPONSE_FIELD].strip())
        
        if isinstance(response, ollama.ChatResponse):
            if MESSAGE_FIELD in response:
                content = response[MESSAGE_FIELD][CONTENT_FIELD]
                return bool(content.strip())

        return False

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
                if RESPONSE_FIELD in chunk and chunk[RESPONSE_FIELD]:
                    has_content = True
                elif MESSAGE_FIELD in chunk and isinstance(chunk[MESSAGE_FIELD], dict) and chunk[MESSAGE_FIELD].get(CONTENT_FIELD):
                    has_content = True
                
                valid_chunks += 1
            elif isinstance(chunk, str):
                # String format - try to parse as JSON
                try:
                    parsed = json.loads(chunk)
                    if isinstance(parsed, dict):
                        if parsed.get(DONE_FIELD):
                            has_done = True
                        if RESPONSE_FIELD in parsed and parsed[RESPONSE_FIELD]:
                            has_content = True
                        elif MESSAGE_FIELD in parsed and isinstance(parsed[MESSAGE_FIELD], dict) and parsed[MESSAGE_FIELD].get(CONTENT_FIELD):
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
        async with httpx.AsyncClient(timeout=httpx.Timeout(HTTP_TIMEOUT_SEC)) as http_client:
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
            if "rag" not in agents:
                raise ValueError("RAG agent not loaded")
            if "moa" not in agents:
                raise ValueError("MoA agent not loaded")

    async def run_all_tests(self):
        """Run all endpoint tests."""
        async with self.server_context():
            test_results = []
            # Test definitions
            tests = []
            
            # Test streaming for all models (both generate and chat)
            # for model in TEST_MODELS_LIST:
            #     tests.append((f"Generate Streaming ({model})", self.test_generate_endpoint_streaming, model))
            #     tests.append((f"Chat Streaming ({model})", self.test_chat_endpoint_streaming, model))
            
            # Uncomment other tests as needed
            tests.extend([
                # ("Generate Endpoint", self.test_generate_endpoint),
                # ("Generate with Agent", self.test_generate_endpoint_with_example_agent),
                # ("Generate Streaming", self.test_generate_endpoint_streaming),
            
                # ("Generate with Optimizer Agent (Positive)", self.test_generate_endpoint_with_optimizer_agent, TEST_PROMPT_OPT_POSITIVE),
                # ("Generate with Optimizer Agent (Negative)", self.test_generate_endpoint_with_optimizer_agent, TEST_PROMPT_OPT_NEGATIVE),
                # ("Generate with RAG Agent", self.test_generate_endpoint_with_rag_agent),
                ("Generate with MoA Agent", self.test_generate_endpoint_with_moa_agent),

                # ("Tags Endpoint", self.test_tags_endpoint),

                # ("Health Endpoint", self.test_health_endpoint),
                # ("Plugins Endpoint", self.test_plugins_endpoint),
                # ("Chat with Agent", self.test_chat_endpoint_with_example_agent),
                # ("Chat Streaming", self.test_chat_endpoint_streaming),
                # ("Chat with Optimizer Agent (Positive)", self.test_chat_endpoint_with_optimizer_agent, TEST_PROMPT_OPT_POSITIVE),
                # ("Chat with Optimizer Agent (Negative)", self.test_chat_endpoint_with_optimizer_agent, TEST_PROMPT_OPT_NEGATIVE),
                # ("Chat with RAG Agent", self.test_chat_endpoint_with_rag_agent),
                ("Chat with MoA Agent", self.test_chat_endpoint_with_moa_agent),
            ])

            for test_def in tests:
                test_name = test_def[0]
                test_func = test_def[1]
                args = test_def[2:] if len(test_def) > 2 else ()
                result = await self._run_single_test(test_name, test_func, *args)
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