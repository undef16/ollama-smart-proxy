### Revised Specification for Creating a New Plugin: "Optimizer Agent" in ollama-smart-proxy
#### 1. Overview
- **Plugin Name**: `optimizer`
- **Purpose**: This plugin acts as an intelligent agent within the ollama-smart-proxy system to dynamically optimize LLM inference parameters (e.g., context window, batch size) based on analyzed input messages and historical request statistics. It aims to improve performance (speed and resource efficiency) without significantly degrading response quality, as per the guidelines discussed (e.g., minimal changes to coherence or accuracy). Additionally, it incorporates a SimHash-based mechanism for detecting similar or identical prompt templates to automatically adapt the context window size based on recognized patterns in prompts, where variable parts (e.g., tails) may change.
- **Repository Integration**: The plugin will be added to the `src/plugins/` directory of https://github.com/undef16/ollama-smart-proxy. It will be activated via the `config.json` file (if needed for overrides) and invoked through slash commands in user messages (e.g., `/opt`).
- **Key Requirements**:
  - Compatibility with Ollama backend (primary focus); extensibility for llama.cpp if a custom client is implemented in the future.
  - Use asynchronous processing to avoid blocking the main proxy flow.
  - Store statistics persistently (e.g., in a lightweight DB like SQLite) for cross-session learning, including SimHash fingerprints for prompt templates.
  - Focus on parameters with significant performance impact: `num_ctx` (context window), `num_batch` (batch size). Exclude `keep_alive` as it is already handled by the core system.
  - Ensure optimizations are reversible and include safeguards against quality drops (e.g., via heuristic checks).
  - Integrate SimHash for prompt similarity detection to enable self-adaptive window sizing.

#### 2. Functional Requirements
- **Activation Mechanism**:
  - Triggered by a slash command in the user message, e.g., `/opt [optional args] <user query>`.
  - If no command is used, the plugin could optionally run in "always-on" mode if configured (e.g., via a flag in a plugin-specific config if needed).
- **Preprocessing (Request Handling)**:
  - Analyze the incoming message: Compute token counts for the current input and full context (system prompt + history + input).
  - Use SimHash to detect similar prompt templates and adapt the context window (see section 2.1 for details).
  - Compare with stored statistics (e.g., average token lengths, past latencies).
  - Dynamically adjust LLM parameters for the current request. If no relevant data exists in statistics or templates, do not change the request and pass it as is to Ollama.
  - Tokenization: Use a simple estimator (e.g., len(text.split()) * 1.3) or integrate a lightweight tokenizer if available (avoid heavy deps); align with the model's tokenizer for accuracy in SimHash.
- **Postprocessing (Response Handling)**:
  - Log response metrics (e.g., latency, tokens generated, memory usage).
  - Update stored statistics and SimHash template data for future optimizations.
  - Optionally, evaluate quality proxy (e.g., response length or basic coherence check) and revert params if issues detected.
- **Statistics Storage**:
  - Use a persistent store (e.g., SQLite file) located in the plugin directory (e.g., `src/plugins/optimizer/data/optimizer_stats.db`).
  - Schema example: Table `request_stats` with columns: id, timestamp, input_tokens, context_tokens, latency, quality_score.
  - Additional table `templates` for SimHash data: id, template_id, window_size, rep_hash (binary or string), observation_count, avg_distance, working_window.
- **Optimization Logic**:
  - **Context Window (`num_ctx`)**: Use SimHash-detected template to adaptively set based on the maximum stable prefix (see section 2.1). If history is long, summarize or truncate non-essentials.
  - **Batch Size (`num_batch`)**: Find the minimal optimal value without drastically increasing latency; reduce if high memory usage.
  - **Dynamic Adjustment**: Use simple rules or moving averages from stats. For similar inputs (e.g., via length similarity or SimHash), apply proven params. Defer any ML-based predictions (e.g., via scikit-learn) to future implementations.
- **2.1 Prompt Template Detection with SimHash**:
  - **Measurement**: Use SimHash to generate bit fingerprints (e.g., 64 or 128 bits). Similarity via Hamming distance: `similarity = 1 - (dist / B)`, where B is bit length. Target ~80% similarity (e.g., dist <=12 for B=64).
  - **Multi-Resolution Prefixes**: For each prompt, compute SimHash for prefixes of varying window sizes W (e.g., {64, 128, 256, 512, 1024} tokens). Use token shingles (3-5 tokens) for robustness.
  - **Online Algorithm**:
    - **Step A (Matching)**: For new prompt P, compute simhash(P, W) for all W. Start from largest W to smallest; find matching existing template within threshold k(W) by Hamming distance. Stop at first match: this W* is the max stable prefix.
    - **Step B (Update Template)**: For each template, store rep_hash[W] as bitwise majority vote over observed fingerprints. Track observation count and distance stats.
    - **Step C (Adapt Window)**: Maintain working_window per template. Shrink if match fails on current but succeeds on smaller; grow if consistent matches on larger W over 20-50 observations.
  - **Efficiency**: For many templates, split fingerprints into k+1 blocks and index for fast candidate retrieval.
  - **Parameters**: B=64 bits; W grid: 64/128/256/512/1024; k=3-6 for strict matching (adjust for >=80% if needed); shingles 3-5.
  - **Avoid Collisions**: Prioritize largest matching W to distinguish templates with similar starts (e.g., different tasks like resume scoring vs. cover letter adaptation).
- **Error Handling**: Log issues (e.g., OOM, SimHash computation errors). Do not crash the proxy.

#### 3. Technical Specifications
- **Language & Dependencies**:
  - Python 3.12+ (matching repo).
  - Core deps: From repo's `pyproject.toml` (e.g., asyncio, pynvml for GPU if present).
  - Additional: `sqlite3` (built-in) for storage; `psutil` for system metrics (add to dependencies if not already included, as it is lightweight and essential for CPU/GPU monitoring); `simhash-py` or implement SimHash manually (lightweight, no heavy deps; prefer simple implementation using hashlib for hashing).
  - No new external installs beyond justification; leverage proxy's existing utils (e.g., any VRAM estimation tools if present in shared utils). For tokenization in SimHash, use model's tokenizer via Ollama API if accessible, or fallback to simple splitter.
- **File Structure**:
  - Place in `src/plugins/optimizer/` subdirectory with `agent.py` (for the agent implementation), `simhash_utils.py` (for SimHash logic if separated).
  - Include a `data/` subdir for the DB (e.g., `optimizer_stats.db`).
- **Interface & Hooks** (Based on Repo Architecture):
  - Inherit from `BaseAgent` (from `src.shared.base_agent`).
  - Key Class and Methods to Implement:
    - `class OptimizerAgent(BaseAgent):`
      - `@property def name(self) -> str: return 'opt'` # For slash command registration as `/opt`.
      - `async def on_request(self, context) -> Any:` Analyze input (e.g., context.messages or context.request.messages), compute tokens/context/SimHash, detect template, adjust params (e.g., modify context.options or equivalent). Return updated context.
        - `context`: Likely a context object or dict containing request data (e.g., messages, model, options); infer from usage as a mutable structure for preprocessing.
      - `async def on_response(self, context) -> Any:` Log metrics, update DB and SimHash templates. Return modified context/response if needed.
      - Optional: `__init__(self)` or class method for initialization: Setup DB in plugin dir, load stats and templates.
  - Integration: The proxy imports plugins dynamically via `plugin_registry.py` and calls these hooks in the chat/generate slices. Ensure compatibility with the agent routing in `slices/chat/` or similar.
- **Configuration**:
  - Do not modify the app's main `config.json`. Instead, use a plugin-specific config file (e.g., `src/plugins/optimizer/config.json`) for settings like `default_buffer_multiplier`, `always_on`, SimHash params (e.g., bit_length=64, window_grid=[64,128,256,512,1024], hamm_thresholds={64:3,128:4,...}).
  - Allow overrides for volume/load (e.g., unique_templates, daily_requests) to tune W grid or k(W).
- **Testing**:
  - Unit tests: Mock context, verify param adjustments and SimHash matching.
  - Integration: Use repo's `tests/` style; run with pytest. Test SimHash on sample prompts with variations.
  - E2E: Simulate via `main_sim.py`; check performance gains (e.g., 20-50% speed) and accurate template detection/adaptation.

#### 4. Implementation Guidelines for AI Coding Agent
- **Step-by-Step Coding Flow**:
  1. Import necessary modules: From `src.shared.base_agent`, `src.entities` (if present for Message models), `src.utils` (if any), `asyncio`, `sqlite3`, `hashlib` (for SimHash).
  2. Define DB setup in `__init__` or a class method: Create tables if not exists, using a path relative to the plugin dir (e.g., via `os.path.dirname(__file__)`).
  3. Implement token estimation and SimHash: Functions for approx tokens, shingle hashing, fingerprint computation, Hamming distance.
  4. In `on_request`: Parse slash command if needed (though handled by proxy), compute full context from context.messages, compute multi-W SimHash, match/update templates, adapt working_window, set optimal params and update context.options.
  5. In `on_response`: Insert stats to DB, update template rep_hash and stats via majority vote.
  6. Handle async: Use `async def` and `await` for any I/O operations (e.g., DB queries).
- **Best Practices**:
  - Follow the repo's architecture: Keep business logic in methods; avoid tight coupling.
  - Logging: Use proxy's logging (e.g., via `logging` module).
  - Performance: Keep analysis lightweight (<100ms overhead); SimHash is fast for short prefixes.
  - Edge Cases: Handle empty history, very long inputs, multi-GPU, varying prompt lengths, template collisions.
- **Potential Extensions**: Future ML for better predictions or advanced indexing, but exclude from initial version.

#### 5. Deliverables
- Code: `src/plugins/optimizer/agent.py`, `src/plugins/optimizer/simhash_utils.py` (and `data/` for DB).
- Optional plugin config: `src/plugins/optimizer/config.json` if needed.
- Documentation: Add a README in plugin dir or update main README, including SimHash details and references.
- Pull Request: Fork repo, implement, test, submit PR with description.