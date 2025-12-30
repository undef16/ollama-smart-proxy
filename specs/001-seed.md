# Ollama Smart Proxy

**Technical Specification (VSA Aligned)**

---

## 1. Introduction

### 1.1 Project Overview

Ollama Smart Proxy is a lightweight, extensible proxy server for a single Ollama server. It exposes **Ollama-compatible OpenAI-style APIs** and extends functionality via a **dynamic agent (plugin) architecture**.

The proxy supports:

* Dynamic **model loading based on client requests** (handled by the Ollama server).
* Modular **agent plugins** for request and response processing.
* **Prompt-driven agent activation** using slash commands.
* Simple configuration and deployment.

### 1.2 Objectives

* Interact with a single Ollama server with minimal operational complexity.
* Dynamically load models specified by clients at request time.
* Enable request/response customization via modular agents.
* Maintain strict isolation between features (Slices) to ensure maintainability.

### 1.3 Core Concepts

| Concept | Description |
| --- | --- |
| **Model-Driven Init** | Server model is determined by the client `model` field. |
| **Agents** | Plugins that modify requests and/or responses. |
| **Agent Chain** | Ordered sequence of agents activated per request. |
| **Slash Commands** | Prompt prefixes that activate agents dynamically (e.g., `/rag`). |
| **Shared Kernel** | Common infrastructure used by slices (Config, Logging, Plugin Registry). |

---

## 2. Architecture

### 2.1 High-Level Design (Vertical Slice)

The proxy is structured into **Features (Slices)** and **Shared Kernel**.

* **Slices** are distinct user-facing features (endpoints). They contain *all* the logic required to fulfill a specific request type. Slices **never** depend on other slices.
* **Shared Kernel** contains the foundational code (config, client wrappers, plugin registry) that Slices import to do their job.

#### A. The Vertical Slices (Features)

1. **Chat Endpoint Slice** (`POST /api/chat`)
* **Responsibility:** Handles the core chat flow.
* **Logic:** Request parsing, model resolution, slash command extraction, agent chain execution, and upstream forwarding.


2. **Health Endpoint Slice** (`GET /health`)
* **Responsibility:** Operational monitoring.
* **Logic:** Pings the upstream server and checks local proxy status.


3. **Plugin Admin Slice** (`GET /plugins`)
* **Responsibility:** Introspection.
* **Logic:** Returns a JSON list of loaded agents and their status (reads from Shared Registry).


4. **Pass-Through Slices** (e.g., `POST /api/embeddings`, `GET /api/tags`)
* **Responsibility:** Forwarding standard Ollama requests that do not require agent processing.
* **Logic:** Minimal parsing and direct forwarding using the Shared Ollama Client.



#### B. The Shared Kernel (Infrastructure)

* **Configuration:** Global settings loading (Pydantic models).
* **Plugin Registry:** A singleton service that scans disk, loads agent code, and provides access to agent instances.
* **Ollama Client Wrapper:** A centralized HTTP client for upstream communication.
* **Async Primitives:** Shared `asyncio.Lock` instances for thread-safe state management.

### 2.2 Data Flow (Authoritative)

1. **Client Request:** Client sends `POST /api/chat`.
2. **Routing:** FastAPI routes directly to the **Chat Endpoint Slice**.
3. **Slice Execution:**
* *Import:* Slice imports `PluginRegistry` from Shared Kernel.
* *Parse:* Slice extracts slash commands (e.g., `/rag`).
* *Resolve:* Slice asks `PluginRegistry` for the specific agents requested.
* *Chain:* Slice executes the agent chain (Request Hooks).
* *Forward:* Slice uses `OllamaClient` (Shared Kernel) to send to Ollama.
* *Response:* Slice executes agent chain (Response Hooks).


4. **Response:** Final response returned to client.

### 2.3 Technology Stack

* **Language:** Python 3.12+
* **Framework:** FastAPI (Async/Await native).
* **Concurrency:** `asyncio` (Event loop) + `asyncio.Lock` for shared state. **Strictly no blocking `threading.Lock**`.
* **LLM Backend:** `ollama` Python library (wrapped in async adapter).

---

## 3. Server Management & Shared Kernel

### 3.1 Server Characteristics

* Single Ollama server instance.
* Models are **lazily loaded** by upstream Ollama.

### 3.2 Global Configuration (Shared)

* Loaded once at startup.
* Injected into Slices via Dependency Injection or Singleton import.

### 3.3 Plugin Registry (Shared)

* **Responsibility:** Scans `plugins_dir` at startup.
* **State:** Holds references to instantiated Agent classes.
* **Thread Safety:** Uses `asyncio` primitives if dynamic reloading is added.

---

## 4. Model Loading (Chat Slice Logic)

### 4.1 Logic Placement

All logic regarding `model` field parsing and validation resides **exclusively inside the Chat Slice**. Other slices (like Health) do not care about request-specific model loading.

### 4.2 Resolution Rules

1. Extract `model` string from JSON body.
2. Parse `model:tag`.
3. Pass to Upstream via `OllamaClient`.

---

## 5. Plugin and Agent Architecture

### 5.1 Discovery (Infrastructure)

* The **Plugin Registry** (Shared Kernel) scans the directory structure.
* **Structure:**
```
plugins/
├── rag_agent/
│   ├── agent.py  (Must implement BaseAgent interface)
│   └── config.json

```



### 5.2 Agent Interface (Contract)

Agents must adhere to an async interface to ensure they don't block the FastAPI event loop.

```python
class BaseAgent:
    async def on_request(self, payload: dict) -> dict: ...
    async def on_response(self, response: str) -> str: ...

```

---

## 6. Agent Chain Execution (Chat Slice Logic)

### 6.1 Logic Placement

The *logic* of how to chain agents (Sequential, Parallel, etc.) belongs to the **Chat Slice**. The Shared Kernel only provides the *list* of agents.

### 6.2 Execution Flow

1. **Parsing:** `Chat Slice` detects `/rag /translate` in prompt.
2. **Lookup:** `Chat Slice` requests "rag" and "translate" objects from `PluginRegistry`.
3. **Execution:** `Chat Slice` iterates through them:
* `await agent.on_request(context)`


4. **Isolation:** Agent state is ephemeral or passed via the context dictionary to ensure request isolation.

---

## 7. API Behavior

### 7.1 Chat Slice

* **Endpoint:** `/api/chat`
* **Features:** Agent support, Slash commands.

### 7.2 Pass-Through Slices

* **Endpoints:** `/api/tags`, `/api/generate`, `/api/embeddings`
* **Features:** No agent support. Pure proxying.
* *Note:* These are separate router definitions to allow future specific logic (e.g., caching embeddings) without touching the Chat Slice.

---

## 8. Deployment

* **Entry Point:** `main.py` (Bootstraps Shared Kernel, then mounts Slices).
* **Orchestration:** None required (Python process).

---

## 9. Error Handling

### 9.1 Philosophy

* **Shared Kernel:** Defines custom Exception classes (e.g., `UpstreamConnectionError`, `PluginExecutionError`).
* **Slices:** Catch these exceptions and decide the HTTP response (e.g., 502 Bad Gateway vs 200 OK with error message in body).

### 9.2 Reliability

* If an Agent crashes, the Chat Slice catches the exception, logs it, and decides whether to abort or continue without that agent (Soft Failure).

---

## 10. Testing and Observability

### 10.1 Testing Strategy

* **Unit Tests:** Test individual Agents in isolation.
* **Slice Tests:** Test `/api/chat` using a mock `PluginRegistry` and mock `OllamaClient`.
* **Integration:** Full system test with a real Ollama instance.

### 10.2 Observability

* **Logging:** Structured logging injected from Shared Kernel.
* **Metrics:** Slices report specific metrics (e.g., "Agents Activated Count") to a central collector if needed.

