# Specification of the `/rag` plugin for Ollama Smart Proxy

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
* **Storage Drivers (via LightRAG):**
* *Graph:* Neo4j (via `Neo4JStorage').
* *KV/Vector/Status:* PostgreSQL + Apache AGE (via `PGKVStorage`, `PGVectorStorage').


* **External Search:** SearxNG (fallback with low relevance).
* **Inference:** Ollama (via LangChain).

---

## 2. The algorithm of operation (LangGraph)

The state machine manages the transition between nodes based on the relevance threshold **0.6** .

### Nodes of the graph (Nodes):

1. **Retrieve:** Calling `lightrag.query(mode="mix")` to get the context from the local graph and vectors.


2. **Grade:** LLM-evaluation of received documents. Each document is assigned a status: `relevant` or `irrelevant'.


3. **Web Search:** If there is no relevant data (all is `irrelevant' or the average score is < 0.6), a request is made to **SearxNG**.


4. **Transform Query:** Optimization of the user's query for the search engine before calling searchxng.


5. **Inject & Finalize:** Assembling the resulting context and embedding it in the prompt for Ollama.

### Transition Logic (Edges):

* `Retrieve` -> `Grade`
* `Grade` -> `Inject' (if at least one relevant document > 0.6 is found).
* `Grade` -> `Transform Query` -> `Web Search` -> `Inject` (if local data is weak).



---

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
    kv_storage="PGKVStorage", # Storing chunks in Postgres
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
* **Speed:** LightRAG provides high efficiency of tokens when searching in the graph (up to 6000x compared to the basic GraphRAG).