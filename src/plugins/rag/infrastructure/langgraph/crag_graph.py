"""CRAG (Corrective RAG) LangGraph implementation."""
import json

from typing import List, TypedDict

from langgraph.graph import StateGraph
from langgraph.constants import END
from langchain_ollama import OllamaLLM

from src.plugins.rag.domain.entities.document import Document
from src.plugins.rag.domain.entities.query import Query
from src.plugins.rag.domain.ports.rag_repository import RagRepository
from src.plugins.rag.domain.ports.search_service import SearchService
from src.plugins.rag.infrastructure.config import ConfigurationManager
from src.plugins.rag.infrastructure.resilience import (
    CircuitBreakerRegistry
)
from src.plugins.rag.infrastructure.logging import (
    LoggingUtils, ExternalServiceError, GradingError,
    RetrievalError
)
from src.plugins.rag.infrastructure.error_handler import ErrorHandler
from src.shared.config import Config

logger = LoggingUtils.get_rag_logger(__name__)


class CRAGState(TypedDict):
    """State for the CRAG graph."""
    query: str
    documents: List[Document]
    relevant_documents: List[Document]
    web_documents: List[Document]
    context: str
    web_search_attempts: int


class CRAGGraph:
    """CRAG (Corrective RAG) state machine using LangGraph."""

    def __init__(self, rag_repository: RagRepository, search_service: SearchService):
        """Initialize the CRAG graph.

        Args:
            rag_repository: Repository for local RAG operations.
            search_service: Service for external web search.
        """
        self.rag_repository = rag_repository
        self.search_service = search_service
        self.config = ConfigurationManager.get_config()

        # Get app config for Ollama settings
        app_config = Config()

        # Initialize LLM for grading
        self.llm = OllamaLLM(
            model=self.config.llm_model,
            base_url=f"{app_config.ollama_host}:{app_config.ollama_port}"
        )

        # Initialize circuit breaker for Ollama service
        self.ollama_circuit_breaker = CircuitBreakerRegistry.get_service_circuit_breaker(
            service_name="ollama",
            failure_threshold=self.config.circuit_breaker_failure_threshold,
            recovery_timeout=self.config.circuit_breaker_recovery_timeout,
            success_threshold=self.config.circuit_breaker_success_threshold,
            timeout=self.config.timeout  # Use configured timeout for Ollama calls
        )

        # Build the graph
        self.graph = self._build_graph()
        logger.debug("CRAG graph initialized")

    def _build_graph(self):
        """Build the CRAG state graph."""
        graph = StateGraph(CRAGState)

        # Add nodes
        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("grade", self._grade_node)
        graph.add_node("transform_query", self._transform_query_node)
        graph.add_node("web_search", self._web_search_node)
        graph.add_node("grade_web", self._grade_web_node)
        graph.add_node("inject", self._inject_node)

        # Add edges
        graph.add_edge("retrieve", "grade")
        graph.add_conditional_edges(
            "grade",
            self._should_web_search,
            {
                "inject": "inject",
                "transform_query": "transform_query"
            }
        )
        graph.add_edge("transform_query", "web_search")
        graph.add_edge("web_search", "grade_web")
        graph.add_conditional_edges(
            "grade_web",
            self._should_retry_or_inject,
            {
                "inject": "inject",
                "transform_query": "transform_query"
            }
        )
        graph.add_edge("inject", END)

        # Set entry point
        graph.set_entry_point("retrieve")

        self.compiled_graph = graph.compile()

    @ErrorHandler.log_error_context("crag_pipeline", component="crag_graph")
    async def run(self, query_text: str) -> str:
        """Run the CRAG pipeline for a query.

        Args:
            query_text: The user query text.

        Returns:
            The assembled context for injection.

        Raises:
            RetrievalError: If document retrieval fails
            GradingError: If document grading fails
            ExternalServiceError: If external services fail
            InjectionError: If context injection fails
        """
        if not query_text or not query_text.strip():
            error = RetrievalError(
                "Query text cannot be empty",
                query=query_text,
                suggestions=["Provide a non-empty query text"]
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

        try:
            logger.info(f"Running CRAG pipeline for query: {query_text}")

            initial_state: CRAGState = {
                "query": query_text,
                "documents": [],
                "relevant_documents": [],
                "web_documents": [],
                "context": "",
                "web_search_attempts": 0
            }

            result = await self.compiled_graph.ainvoke(initial_state)
            context = result.get("context", "")

            # Only raise error if context is empty AND we didn't reach the passthrough node intentionally
            # Passthrough node is designed to return empty context when no relevant documents found
            if not context:
                logger.info("CRAG pipeline completed with empty context (passthrough)")
            else:
                logger.info(f"CRAG pipeline completed, context length: {len(context)}")
            
            return context

        except RetrievalError:
            # Re-raise retrieval errors as-is
            raise
        except GradingError:
            # Re-raise grading errors as-is
            raise
        except ExternalServiceError:
            # Re-raise external service errors as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            error = RetrievalError(
                f"Unexpected error in CRAG pipeline: {str(e)}",
                query=query_text,
                suggestions=[
                    "Check system logs for detailed error information",
                    "Verify all dependent services are operational",
                    "Review CRAG pipeline configuration"
                ],
                cause=e
            )
            LoggingUtils.log_structured_error(error, logger)
            raise error

    async def _retrieve_node(self, state: CRAGState) -> CRAGState:
        """Retrieve documents from local RAG knowledge base."""
        logger.debug("Executing retrieve node")

        query = Query(text=state["query"])
        documents = self.rag_repository.query(query)

        logger.debug(f"Retrieved {len(documents)} documents from local RAG")
        return {
            **state,
            "documents": documents
        }

    async def _grade_documents(self, documents: List[Document], query: str) -> List[Document]:
        """Common method to grade document relevance."""
        if not documents:
            logger.debug("No documents to grade")
            return []

        # Prepare batch grading prompt
        prompt = self._prepare_batch_grading_prompt(documents, query)

        try:
            # Make single LLM call for all documents
            llm_response = await self.ollama_circuit_breaker.call(
                self.llm.ainvoke, prompt, {"format": "json"}
            )
            response = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

            if not response or not response.strip():
                logger.warning("LLM returned empty response for batch grading, using fallback")
                relevant_documents = []
            else:
                # Check if response contains non-JSON content that indicates failure
                response_lower = response.lower().strip()
                if (response_lower in ["mark this task complete.", "complete.", "done.", "success."] or
                    "task" in response_lower and "complete" in response_lower):
                    logger.warning(f"LLM returned task completion message instead of JSON: {response}")
                    # Use fallback scores
                    scores = [self.config.default_relevance_score] * len(documents)
                else:
                    # Parse JSON response
                    scores = self._parse_batch_grading_response(response)
                    if len(scores) != len(documents):
                        logger.warning(f"Score count ({len(scores)}) doesn't match document count ({len(documents)}), using defaults")
                        scores = [self.config.default_relevance_score] * len(documents)
                
                # Filter relevant documents based on scores
                relevant_documents = [
                    doc for doc, score in zip(documents, scores)
                    if score >= self.config.rag_threshold
                ]

        except Exception as e:
            logger.warning(f"Batch grading failed: {e}, using fallback (no relevant documents)")
            relevant_documents = []
        
        return relevant_documents

    async def _grade_node(self, state: CRAGState) -> CRAGState:
        """Grade the relevance of retrieved documents using batch LLM call."""
        logger.debug("Executing grade node")

        documents = state["documents"]
        relevant_documents = await self._grade_documents(documents, state["query"])

        logger.debug(f"Graded {len(documents)} documents, {len(relevant_documents)} relevant")
        return {
            **state,
            "relevant_documents": relevant_documents
        }


    def _prepare_batch_grading_prompt(self, documents: List[Document], query: str) -> str:
        """Prepare a batch grading prompt for all documents."""
        # Format documents list for the template
        docs_formatted = "\n".join(f"Document {i}: {doc.content}" for i, doc in enumerate(documents, 1))

        # Use template from config
        template = self.config.relevance_evaluation_prompt_template
        return template.format(query=query, documents=docs_formatted)

    def _parse_batch_grading_response(self, response: str) -> List[float]:
        """Parse the batch grading JSON response."""

        try:
            # First, try to find JSON within the response
            # Find all possible JSON objects and pick the one most likely to contain document scores
            json_candidates = self._find_json_within_response(response, json)
            
            if json_candidates:
                json_str = json_candidates[0][0]  # Get the best candidate
            else:
                logger.warning(f"No valid JSON found in response: {response[:200]}...")
                return []

            # Parse the JSON
            data = json.loads(json_str)

            # Verify that data is a dict (not a string or other type)
            if not isinstance(data, dict):
                logger.warning(f"Parsed JSON is not a dict: {type(data)}, value: {data}")
                return []

            logger.debug(f"Parsed JSON data: {data}")  # Add debugging info
            
            # Extract scores in order based on document count
            scores = self._extract_scores(data)

            logger.debug(f"Generated scores: {scores}")
            return scores

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse batch grading response: {e}")
            logger.debug(f"Response that failed to parse: {response[:500]}...")
            return []
        except Exception as e:
            logger.warning(f"Unexpected error parsing batch grading response: {e}")
            logger.debug(f"Full error: {e}, Response: {response[:500]}...")
            # Make sure we're not propagating string values as exceptions
            if isinstance(e, str) and 'doc_' in e:
                logger.error(f"String containing 'doc_' was raised as exception: {e}")
                return []
            return []

    def _extract_scores(self, data):
        scores = []
        for i in range(1, 100):  # Assume max 100 documents
            key = f"doc_{i}"
                # Safety check: ensure data is still a dict before accessing
            if not isinstance(data, dict):
                logger.warning(f"Data became non-dict during processing: {type(data)}, stopping")
                break
            if key not in data:
                logger.debug(f"Key {key} not found in data, stopping iteration")
                break
            try:
                score = data.get(key)
                if score is None:
                        # If key exists but value is None, use default
                    scores.append(self.config.default_relevance_score)
                elif isinstance(score, (int, float)):
                    scores.append(max(0.0, min(1.0, float(score))))
                elif isinstance(score, str):
                        # Try to convert string to float
                    try:
                        score_float = float(score)
                        scores.append(max(0.0, min(1.0, score_float)))
                    except ValueError:
                        logger.warning(f"Could not convert score '{score}' to float, using default")
                        scores.append(self.config.default_relevance_score)
                else:
                    logger.warning(f"Unexpected score type {type(score)} for {key}: {score}, using default")
                    scores.append(self.config.default_relevance_score)
            except Exception as e:
                logger.warning(f"Error processing score for {key}: {e}, using default")
                scores.append(self.config.default_relevance_score)
        return scores

    def _find_json_within_response(self, response, json):
        start_indices = [i for i, char in enumerate(response) if char == '{']
        json_candidates = []
            
        for start_idx in start_indices:
            brace_count = 0
            for i in range(start_idx, len(response)):
                if response[i] == '{':
                    brace_count += 1
                elif response[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        candidate_json = response[start_idx:i+1]
                        try:
                            parsed = json.loads(candidate_json)
                                # Check if this JSON contains document score keys
                            if isinstance(parsed, dict) and any('doc_' in str(k) for k in parsed.keys()):
                                json_candidates.append((candidate_json, len(parsed)))  # Store with length for sorting
                            else:
                                    # If no doc_ keys, still store it as a backup option
                                json_candidates.append((candidate_json, 0))
                        except json.JSONDecodeError:
                            continue
                        break
            
            # Sort candidates by number of document keys (prefer ones with doc_ keys)
        json_candidates.sort(key=lambda x: x[1], reverse=True)
        return json_candidates

    def _should_web_search(self, state: CRAGState) -> str:
        """Determine if web search is needed based on relevant documents."""
        relevant_docs = state["relevant_documents"]

        if not relevant_docs:
            logger.debug("No relevant documents found, proceeding to web search")
            return "transform_query"
        else:
            logger.debug(f"Found {len(relevant_docs)} relevant documents, proceeding to inject")
            return "inject"

    def _should_retry_or_inject(self, state: CRAGState) -> str:
        """Determine next action based on web document relevance and search attempts."""
        web_documents = state["web_documents"]
        current_attempts = state["web_search_attempts"]
        
        # If we have relevant web documents, inject them
        if web_documents and len(web_documents) > 0:
            logger.debug(f"Found {len(web_documents)} relevant web documents, proceeding to inject")
            return "inject"
        
        # Check if we've exceeded the maximum attempts (3)
        if current_attempts >= 3:
            logger.debug(f"Exceeded maximum web search attempts ({current_attempts}), proceeding to inject with empty context")
            # Return inject but ensure web_documents is empty so inject creates empty context
            # This is handled by the inject node which will create empty context when no documents exist
            return "inject"
        
        # Otherwise, try again with a new query
        logger.debug(f"No relevant web documents found, attempt {current_attempts}/3, proceeding to transform_query")
        return "transform_query"

    async def _transform_query_node(self, state: CRAGState) -> CRAGState:
        """Transform the query using LLM for better web search results."""
        logger.debug("Executing transform query node")

        query = state["query"]

        # Prepare the transformation prompt using the template from config
        prompt_template = self.config.query_transformation_prompt_template
        prompt = prompt_template.format(query=query)

        try:
            # Make LLM call to transform the query
            llm_response = await self.ollama_circuit_breaker.call(
                self.llm.ainvoke, prompt, {"format": "text"}
            )
            response_content = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

            # Clean up the response to extract just the query
            # In case the LLM adds explanations, we just want the query
            transformed_query = self._extract_clean_query(response_content)

        except Exception as e:
            logger.warning(f"Query transformation failed: {e}, using fallback transformation")
            # Fallback to simple transformation
            transformed_query = f"{query} information details facts"

        logger.debug(f"Transformed query: '{query}' -> '{transformed_query}'")
        return {
            **state,
            "query": transformed_query
        }

    def _extract_clean_query(self, response: str) -> str:
        """Extract clean query from LLM response."""
        # Split by newlines and look for the most likely query line
        lines = response.split('\n')
        
        # Look for the first line that seems to be a query (not an explanation)
        for line in lines:
            line = line.strip()
            
            # Skip lines that start with common explanation phrases
            if (line and
                not line.startswith(('The', 'Here', 'A ', 'An ', 'This', 'That', 'In', 'On', 'At', 'To', 'For')) and
                not line.lower().startswith(('here\'s', 'here is', 'the ', 'a ', 'an ', 'this', 'that', 'in ', 'on ', 'at ', 'to ', 'for ')) and
                not line.endswith((':', '.', '?', '!'))):
                
                # Remove potential quote marks and return clean query
                line = line.strip('"\'')
                if line:
                    return line
        
        # If no suitable line found, return the first non-empty line
        for line in lines:
            line = line.strip().strip('"\'')
            if line:
                return line
                
        # Fallback to original response if all else fails
        return response.strip()

    async def _web_search_node(self, state: CRAGState) -> CRAGState:
        """Perform web search for additional context."""
        logger.debug("Executing web search node")

        query = state["query"]
        web_documents = self.search_service.search(query)

        logger.debug(f"Retrieved {len(web_documents)} documents from web search")
        return {
            **state,
            "web_documents": web_documents
        }

    def _handle_web_search_attempts(self, state: CRAGState, relevant_web_documents: List[Document]) -> CRAGState:
        """Handle web search attempts based on whether relevant documents were found."""
        
        current_attempts = state.get("web_search_attempts", 0)
        
        if relevant_web_documents:
            logger.debug(f"Found {len(relevant_web_documents)} relevant web documents")
            # Found relevant documents, reset attempts and return
            return {
                **state,
                "web_documents": relevant_web_documents,
                "web_search_attempts": 0  # Reset attempts since we found relevant docs
            }
        else:
            logger.debug(f"No relevant web documents found, incrementing attempts ({current_attempts + 1}/3)")
            # No relevant documents found, increment attempts
            return {
                    **state,
                    "web_documents": [],  
                    "web_search_attempts": current_attempts + 1
                }
            
    async def _grade_web_node(self, state: CRAGState) -> CRAGState:
        """Grade the relevance of web search documents."""
        logger.debug("Executing grade web node")

        web_documents = state["web_documents"]
        query = state["query"]
        current_attempts = state.get("web_search_attempts", 0)

        if not web_documents:
            logger.debug("No web documents to grade, incrementing attempts")
            # No documents found, increment attempts
            return {
                **state,
                "web_documents": [],  # Ensure web_documents is an empty list
                "web_search_attempts": current_attempts + 1
            }

        # Use the common grading method
        relevant_web_documents = await self._grade_documents(web_documents, query)

        # Store relevant web documents into the RAG system for continuous learning
        if relevant_web_documents:
            try:
                self.rag_repository.store_documents(relevant_web_documents)
                logger.debug(f"Stored {len(relevant_web_documents)} relevant web documents into RAG system")
            except Exception as e:
                logger.warning(f"Failed to store web documents into RAG system: {e}")

        # Handle the result using the common method
        return self._handle_web_search_attempts(state, relevant_web_documents)

    async def _inject_node(self, state: CRAGState) -> CRAGState:
        """Assemble and inject the final context."""
        logger.debug("Executing inject node")

        relevant_docs = state["relevant_documents"]
        web_docs = state["web_documents"]

        # Combine all relevant documents (local RAG + web search results)
        all_docs = relevant_docs + web_docs

        # Assemble context only if there are documents
        if all_docs:
            # Assemble context
            context_parts = []
            for i, doc in enumerate(all_docs[:self.config.max_documents], 1):
                context_parts.append(f"[Document {i}]\n{doc.content}\n")

            context = "\n".join(context_parts)
        else:
            # No documents available - this is the passthrough case
            logger.debug("No documents available, returning empty context (passthrough)")
            context = ""

        logger.debug(f"Assembled context with {len(all_docs)} documents")
        return {
            **state,
            "context": context
        }