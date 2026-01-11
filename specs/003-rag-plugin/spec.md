# Feature Specification: RAG Plugin for Ollama Smart Proxy

**Feature Branch**: `003-rag-plugin`  
**Created**: 2026-01-08  
**Status**: Draft  
**Input**: User description: "# Specification of the `/rag` plugin for Ollama Smart Proxy

Tech stack: LightRAG, searxng, neo4j, ollama, langgraph, langchain, pydantic, CRAG, PostgreSQL with graph extensions. Hexagon architectura. Implement by @https://langchain-ai.github.io/langgraph/tutorials/rag/langgraph_crag/algorithm . 

LightRAG: https://github.com/HKUDS/LightRAG?tab=readme-ov-file

General workflow:
1. App or user provide /rag command in the prompt
2. Proxy retrieve new request
3. Activate rag agent/plugin
4. Route to on_retrieve event in new agent
5. Activate web search if LightRAG doesn't contains relevant document or relevance less than 0.6
6. Prepared embeddings inject to user request prompt
7. Continue evalute app/user request in standard proxy chain
8. On_response event do nothing
9. Return to user/app response from ollama back by proxy.


##1. Architecture and Stack

The plugin implements the **Corrective RAG (CRAG) pattern** within the framework of the hexagonal proxy architecture.

* **Core Logic:** LangGraph (process state machine).
* **RAG Engine:** LightRAG (interface to KG and vector search).
* **Storage Drivers (via LightRAG):*
* *Graph:* Neo4j (via `Neo4JStorage').
* *KV/Vector/Status:* PostgreSQL + Apache AGE (via `PGKVStorage`, `PGVectorStorage').

* **External Search:** SearxNG (fallback with low relevance).
* **Inference:** Ollama (via LangChain).

---

## 2. The algorithm of operation (LangGraph)

The state machine manages the transition between nodes based on the relevance threshold **0.6** .

### Nodes of the graph (Nodes):

1. **Retrieve:** Calling `lightrag.query(mode="mix")` to get the context from the local graph and vectors.


2. **Grade:** LLM-evaluation of received documents. Each document is assigned a status: `relevant` or `irrelevant`.


3. **Web Search:** If there is no relevant data (all is `irrelevant' or the average score is < 0.6), a request is made to **SearxNG**.


4. **Transform Query:** Optimization of the user's query for the search engine before calling searchxng.


5. **Inject & Finalize:** Assembling the resulting context and embedding it in the prompt for Ollama.

### Transition Logic (Edges):

* `Retrieve` -> `Grade`
* `Grade` -> `Inject' (if at least one relevant document > 0.6 is found).
* `Grade` -> `Transform Query` -> `Web Search` -> `Inject` (if local data is weak).


##3. The life cycle of a plugin in a proxy

1. ** interception:** The proxy catches the `/rag` command at the beginning of the prompt.
2. **on_retrieve:**
* The LangGraph agent is activated.
* The CRAG cycle starts.
* LightRAG turns to Neo4j/Postgres for knowledge.
* If there is little knowledge, SearxNG gets it from the network.
* The result (embeddings/text) is packaged in the system context.


3. **Prompt Injection:** The prepared context is inserted into the request body.
4. **Forward:** The request goes into the standard Ollama Smart Proxy chain.
5. **on_response:** Skips the answer (do nothing).

---

## 4. Configuration of LightRAG drivers

Initialization of LightRAG in the plugin must use the specified drivers to work with the database.:

```python
rag = LightRAG(
    working_dir=WORKING_DIR,
    kv_storage="RedisKVStorage", # Storing chunks in Postgres
    vector_storage="PGVectorStorage", # Vectors in pgvector
    graph_storage="Neo4JStorage", # Graph of connections in Neo4j
    doc_status_storage="PGDocStatusStorage" # Indexing statuses
)

```

---

## 5. Environment (.env)

| Variable | Description |
| --- | --- |
| ` NEO4J_URI` | Connecting to Neo4j for `Neo4JStorage` |
| `POSTGRES_URI` | Connecting to PostgreSQL for `PG*Storage` |
| `SEARXNG_HOST` | URL of the SearxNG instance |
| `RAG_THRESHOLD` | Relevance threshold (default: 0.6) |
| `OLLAMA_BASE_URL` | Address of the local Ollama |

---

## 6. Advantages of implementation

* **Simplification:** All SQL/Cypher code is hidden inside LightRAG.


* **Reliability:** LangGraph guarantees a self-check cycle and a fallback to the search.
* **Speed:** LightRAG provides high efficiency of tokens when searching in the graph (up to 6000x compared to the basic GraphRAG)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enable RAG-enhanced responses (Priority: P1)

As a user of the Ollama Smart Proxy, I want to prefix my prompts with /rag so that the system retrieves relevant context from local knowledge base and web search to provide more accurate and informed responses.

**Why this priority**: This is the core functionality of the RAG plugin, enabling enhanced AI responses with contextual information.

**Independent Test**: Can be tested independently by sending a prompt prefixed with /rag and verifying that the response includes injected context from LightRAG or SearxNG, without affecting other proxy functionality.

**Acceptance Scenarios**:

1. **Given** a user prompt starts with "/rag", **When** the proxy receives the request, **Then** the RAG plugin is activated and processes the query.
2. **Given** relevant documents exist in the local knowledge base, **When** the query is processed, **Then** context is retrieved and injected into the prompt.
3. **Given** no relevant local documents are found, **When** the query is processed, **Then** web search via SearxNG is performed and results are injected.

### User Story 2 - Fallback to web search (Priority: P2)

As a user, I want the system to automatically search the web when local knowledge is insufficient, ensuring I always get the most relevant and up-to-date information.

**Why this priority**: Provides reliability and completeness of responses when local data is limited.

**Independent Test**: Can be tested by querying topics not in the local knowledge base and verifying web search is triggered.

**Acceptance Scenarios**:

1. **Given** local query returns relevance score < 0.6, **When** the grade node evaluates, **Then** web search is initiated.
2. **Given** web search results are obtained, **When** processing completes, **Then** the results are injected into the prompt.

### Edge Cases

- What happens when SearxNG service is unavailable? System should handle gracefully and return response based on available local data.
- How does the system handle queries that are too long or complex? Query transformation should optimize for search engines.
- What if the relevance threshold is exactly 0.6? The system should treat it as insufficient and trigger web search.

## Requirements *(mandatory)*

KISS, DRY, OOP

### Functional Requirements

- **FR-001**: System MUST intercept and recognize prompts starting with "/rag" command.
- **FR-002**: System MUST initialize LightRAG with specified storage drivers (Neo4JStorage, PGKVStorage, PGVectorStorage, PGDocStatusStorage).
- **FR-003**: System MUST query LightRAG using mix mode to retrieve relevant documents from local knowledge base.
- **FR-004**: System MUST evaluate retrieved documents for relevance using LLM grading with threshold 0.6.
- **FR-005**: System MUST perform web search via SearxNG when local relevance is insufficient.
- **FR-006**: System MUST transform user queries for optimal search engine performance.
- **FR-007**: System MUST inject retrieved context into the user prompt before forwarding to Ollama.
- **FR-008**: System MUST handle the CRAG algorithm state transitions correctly.
- **FR-009**: System MUST skip response processing in on_response event.

### Key Entities *(include if feature involves data)*

- **Query**: The user's input text after /rag command, used for retrieval and search.
- **Document**: Retrieved context from LightRAG or SearxNG, containing relevant information.
- **Relevance Score**: Numerical score (0-1) indicating how relevant a document is to the query.
- **Knowledge Graph**: Stored in Neo4j, containing relationships between concepts.
- **Vector Embeddings**: Stored in PostgreSQL, used for similarity search.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can receive RAG-enhanced responses within 5 seconds for queries with sufficient local knowledge.
- **SC-002**: System successfully falls back to web search for 95% of queries with low local relevance.
- **SC-003**: Response accuracy improves by at least 30% when using /rag compared to standard prompts.
- **SC-004**: System maintains response times under 10 seconds even with web search fallback.
- **SC-005**: Plugin handles 100 concurrent /rag requests without performance degradation.

## Assumptions

- Neo4j and PostgreSQL databases are properly configured and accessible.
- SearxNG instance is running and accessible.
- Ollama is installed and running locally.
- Required Python packages (LightRAG, LangGraph, LangChain, Pydantic) are available.
- Hexagonal architecture is implemented in the proxy system.