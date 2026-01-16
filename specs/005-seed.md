# Technical Specification: MoA Agent for Ollama Smart Proxy

## 1. Overview

### 1.1 Purpose
This technical specification outlines the design and implementation of a new agent, named `MoAAgent`, for the Ollama Smart Proxy project (https://github.com/undef16/ollama-smart-proxy). The agent will integrate functionality inspired by the LLM Council system from https://github.com/karpathy/llm-council/blob/master/backend/council.py. Specifically, it will enable a multi-stage "council" process to generate and select the best response to a user query by leveraging multiple Ollama models. This enhances the proxy's capabilities by providing higher-quality, consensus-driven answers through diverse model generation, peer ranking, and synthesis.

The MoAAgent will be activated via a slash command in user prompts (e.g., `/moa`), aligning with the existing plugin architecture of the Ollama Smart Proxy.

### 1.2 Scope
- Implement a 3-stage MoA workflow: response collection, ranking, and final synthesis.
- Use configurable Ollama models for the MoA and a designated "chairman" model.
- Ensure compatibility with OpenAI-style chat completions API.
- Handle asynchronous operations to maintain performance.
- Provide configuration options for models, timeouts, and other parameters.
- Exclude: Integration with external APIs beyond Ollama; advanced error recovery beyond basic fallbacks.

### 1.3 Assumptions and Dependencies
- Ollama server is running and accessible via the proxy's configured host/port.
- Multiple models are pulled and available in Ollama (e.g., via dynamic loading in the proxy).
- Python 3.12+ environment with existing proxy dependencies (e.g., asyncio, pydantic).
- No additional package installations required; use built-in libraries and proxy's shared kernel.

## 2. Requirements

### 2.1 Functional Requirements
- **Activation**: Trigger the agent using a slash command (e.g., `/moa [query]`) in the user message.
- **Stage 1 - Response Collection**: Query multiple configured MoA models in parallel to generate responses to the user query.
- **Stage 2 - Ranking**: Anonymize responses, have each MoA model rank them, and parse/aggregate rankings.
- **Stage 3 - Synthesis**: Use a chairman model to generate a final response based on all prior stages.
- **Output**: Return the synthesized response as the proxy's chat completion reply, with optional metadata (e.g., rankings) if requested.
- **Fallbacks**: If a model fails, exclude it and proceed; if chairman fails, return the top-ranked response.

### 2.2 Non-Functional Requirements
- **Performance**: Asynchronous execution to minimize latency; target <300s for full MoA with 2-5 models.
- **Configurability**: Allow users/admins to specify MoA models, chairman model, and parameters via environment variables or agent config.
- **Error Handling**: Log errors; return graceful failures (e.g., "MoA process failed; using default response").
- **Security**: No changes to existing proxy auth; assume queries are sanitized.
- **Testing**: Unit tests for each stage; integration tests with mock Ollama responses.

## 3. Architecture and Design

### 3.1 High-Level Design
The MoAAgent will subclass `BaseAgent` from the proxy's plugin system. It overrides `on_request` to intercept and process the query through the MoA workflow, bypassing the standard single-model inference. The `on_response` method can be used for post-processing if needed (e.g., formatting metadata).

- **Integration Point**: Placed in `src/plugins/moa/agent.py`.
- **Shared Resources**: Use the proxy's Ollama client for model queries, config for settings, and logging.
- **Workflow**:
  1. Parse slash command to extract query.
  2. Run Stage 1: Parallel queries to MoA models.
  3. Run Stage 2: Anonymize, parallel ranking queries, parse and aggregate.
  4. Run Stage 3: Chairman synthesis prompt with all data.
  5. Return final response in OpenAI-compatible format.

### 3.2 Key Components

#### 3.2.1 Configuration
- Environment Variables:
  - `OLLAMA_MoA_MODELS`: Comma-separated list of model names (e.g., "llama3,mistral2,gemma3").
  - `OLLAMA_CHAIRMAN_MODEL`: Single model name (e.g., "gpt-4-like-local-model").
  - `OLLAMA_MoA_TIMEOUT`: Per-query timeout in seconds (default: 300).
  - `OLLAMA_MoA_MAX_MODELS`: Limit on MoA size (default: 3).
- Agent-Specific Config: Load from a `config.json` in the plugin directory if needed.

#### 3.2.2 Stage 1: Response Collection
- Function: `async def collect_responses(query: str, models: List[str]) -> List[Dict[str, str]]`
- Logic:
  - Use `asyncio.gather` to query models via Ollama client.
  - Each query: Standard chat completion with system prompt (e.g., "Respond accurately to the query.").
  - Filter out None/failed responses.
- Output: `[ {"model": "llama2", "response": "..."} , ... ]`

#### 3.2.3 Stage 2: Ranking
- Function: `async def collect_rankings(responses: List[Dict], models: List[str]) -> Dict`
- Logic:
  - Anonymize: Assign labels like "Response A", "Response B".
  - Build ranking prompt: "Evaluate each response's strengths/weaknesses. Provide FINAL RANKING: 1. Response C\n2. Response A\n..."
  - Parallel queries to MoA models.
  - Parse: Use regex to extract ranking order (e.g., r"(\d+)\.\s*Response\s*([A-Z])").
  - Aggregate: Calculate average rank per response (lower better); map back to models.
- Output: Rankings list, label-to-model map, aggregate scores.

#### 3.2.4 Stage 3: Synthesis
- Function: `async def synthesize_final(query: str, stage1: List[Dict], stage2: Dict, chairman: str) -> str`
- Logic:
  - Build prompt: Include query, all responses (with models), all rankings.
  - Instruct: "Synthesize the best answer considering responses, rankings, and consensus."
  - Query chairman model.
- Fallback: If fails, select top-ranked response from aggregate.

#### 3.2.5 Agent Class
```python
from shared.base_agent import BaseAgent
from shared.ollama_client import OllamaClient  # Assuming proxy's client

class MoAAgent(BaseAgent):
    name = "moa"

    async def on_request(self, request: Dict) -> Dict:
        # Parse query from message if slash command
        if not self.is_activated(request):
            return request  # Pass through if not activated
        query = self.extract_query(request)
        models = self.get_moa_models()
        chairman = self.get_chairman_model()
        
        stage1 = await collect_responses(query, models)
        stage2 = await collect_rankings(stage1, models)
        final = await synthesize_final(query, stage1, stage2, chairman)
        
        # Format as OpenAI response
        return {"choices": [{"message": {"content": final}}]}

    def on_response(self, response: Dict) -> Dict:
        return response  # Optional metadata addition
```

### 3.3 Data Flow
- Input: OpenAI-compatible chat request with /moa in message.
- Processing: MoA stages using Ollama client.
- Output: Chat completion response with synthesized answer.

## 4. Implementation Details

### 4.1 Development Steps
1. Create `src/plugins/moa/` directory with `agent.py`.
2. Implement agent class and stage functions.
3. Add config loading in agent init.
4. Handle async queries using proxy's connection pooling.
5. Implement parsing with robust regex/error handling.
6. Test with mock responses.

### 4.2 Potential Challenges
- Latency: Mitigate with parallel queries and timeouts.
- Prompt Length: Truncate if exceeds model limits.
- Model Availability: Check/pull models dynamically via proxy.
- Parsing Failures: Fallback to simple ordering if format broken.

## 5. Testing and Validation
- **Unit Tests**: Mock Ollama responses; test each stage independently.
- **Integration Tests**: Run full MoA with local Ollama; verify output quality.
- **Edge Cases**: Empty MoA, all failures, long queries.
- **Performance Tests**: Measure latency with varying model counts.

## 6. Deployment and Usage
- **Setup**: Add to `src/plugins/`; restart proxy.
- **Usage Example**:
  - Request: `{"messages": [{"role": "user", "content": "/moa What is the capital of France?"}]}`
  - Response: Synthesized answer, e.g., "The capital of France is Paris."
- **Monitoring**: Use proxy's health endpoints; log MoA metrics.

## 7. Future Enhancements
- Support for weighted rankings or custom prompts.
- Integration with proxy's caching for repeated MoAs.
- UI for visualizing rankings in responses.

This specification provides a complete blueprint for implementing the MoAAgent, ensuring it aligns with the Ollama Smart Proxy's extensible design while delivering advanced LLM orchestration.


Prompts:
ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""


chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""
