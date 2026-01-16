# Mixture of Agents (MoA) Agent Documentation

## Overview

The Mixture of Agents (MoA) agent is a sophisticated component of the Ollama Smart Proxy that enhances response quality through multi-model consensus. Rather than relying on a single model's output, MoA leverages multiple Ollama models to generate responses, evaluates their quality through peer ranking, and selects the best response based on aggregated scores.

## Architecture

The MoA agent operates in two distinct stages:

### Stage 1: Parallel Response Collection
- Collects responses from multiple configured Ollama models simultaneously
- Each model receives the same query and generates an independent response
- Failed model queries are gracefully handled and excluded from further processing

### Stage 2: Peer Ranking and Selection
- For 2 models: Uses circular evaluation where each model evaluates the other's response
- For 3+ models: Uses n+1/n+2 evaluation where each response is evaluated by the next 2 models in sequence
- Aggregates scores to determine the best response
- Returns the response with the highest average score

## Configuration

### Configuration File (`src/plugins/moa/config.json`)

```json
{
  "moa_models": ["gemma3:1b", "gemma3:1b", "gemma3:1b"],
  "timeout": 300,
  "max_models": 3,
  "prompts": {
    "ranking_prompt": "You are evaluating the model's response to the following question:\n\nQuestion: {query}\n\nResponse: {previous_response}\n\nYour task is to evaluate this response and return a score from 0 to 1, where 0 means the response is completely inadequate and 1 means the response is perfect.\n\nProvide your evaluation as a ONLY JSON object with the key 'score' containing the ONLY numerical value.\n\nExample: {\"score\": 0.75}",
    "batch_ranking_prompt": "You are evaluating multiple model responses to the following question:\n\nQuestion: {query}\n\nResponses to evaluate:\n{responses}\n\nYour task is to evaluate each response and return scores from 0 to 1, where 0 means the response is completely inadequate and 1 means the response is perfect.\n\nProvide your evaluation as a JSON array ONLY with objects containing 'response_id' and 'score' fields ONLY without any additional text or score describe.\n\nExample: [{\"response_id\": 0, \"score\": 0.75}, {\"response_id\": 1, \"score\": 0.85}]"
  }
}
```

### Environment Variables

The MoA agent supports configuration via environment variables that take precedence over the configuration file:

- `OLLAMA_MOA_MODELS`: Comma-separated list of models for MoA processing (e.g., `gemma3:1b,llama3.2,mistral`)
- `OLLAMA_MOA_TIMEOUT`: Timeout in seconds for individual model queries (e.g., `300`)
- `OLLAMA_MOA_MAX_MODELS`: Maximum number of models to use (e.g., `3`)

## Usage

### Activating MoA

To use the MoA agent, prefix your query with `/moa`. The agent will intercept the request and process it through the two-stage MoA workflow.

**Example:**
```
/moa What is the difference between artificial intelligence and machine learning?
```

### Request Flow

1. User sends a request starting with `/moa`
2. MoA agent detects the command and extracts the query
3. The two-stage process begins:
   - Stage 1: Parallel queries to configured models
   - Stage 2: Peer evaluation and ranking
4. The highest-scoring response is returned in Ollama-compatible format

## Technical Implementation

### Class Structure

The `MoAAgent` class inherits from `BaseAgent` and implements the following key methods:

#### Core Methods

- `extract_query(request)`: Extracts the query after removing the `/moa` prefix
- `on_request(request)`: Main entry point that orchestrates the MoA workflow
- `on_response(request, response)`: Optional post-processing (currently unused)

#### Stage-Specific Methods

- `collect_responses(query, models)`: Stage 1 - Parallel model querying
- `collect_rankings(query, responses, models)`: Stage 2 - Peer evaluation and ranking selection

#### Strategy Pattern Implementation

The plugin uses a strategy pattern for different ranking approaches:

- `TwoModelsRankingStrategy`: For 2 models using circular evaluation
- `MultiModelsRankingStrategy`: For 3+ models using n+1/n+2 evaluation

### Error Handling

The MoA agent implements robust error handling:

- **Model Failures**: Failed model queries are excluded from processing; the workflow continues with available responses
- **Complete Failure**: If all models fail, an appropriate error response is returned
- **Timeouts**: Configurable timeouts prevent hanging requests
- **JSON Parsing**: Graceful handling of malformed scoring responses from models

### Response Format

The MoA agent returns responses in Ollama-compatible format:

For chat requests:
```json
{
  "message": {
    "role": "assistant",
    "content": "Selected response from MoA..."
  },
  "done": true
}
```

For generate requests:
```json
{
  "response": "Selected response from MoA...",
  "done": true
}
```

## Performance Considerations

### Timing
- The complete MoA process typically takes longer than a single model query due to the multi-stage workflow
- Configurable timeouts help manage response times
- Parallel processing of Stage 1 minimizes delays

### Resource Usage
- Each stage consumes Ollama resources proportional to the number of configured models
- Memory usage scales with response size and model count
- Network traffic increases due to multiple API calls per request

### Scalability
- The system supports concurrent MoA requests
- Asynchronous implementation prevents blocking
- Model limits help control resource consumption

## Troubleshooting

### Common Issues

1. **Models Not Available**: Ensure all configured models are loaded in Ollama
2. **Slow Responses**: Check timeout settings and model availability
3. **Empty Results**: Verify the query follows the `/moa` format correctly
4. **Configuration Issues**: Environment variables override config file settings

### Debugging

Enable logging to track the three-stage process:

- Stage 1: Response collection from individual models
- Stage 2: Peer evaluation and ranking
- Stage 3: Chairman synthesis
- Error handling and fallback mechanisms

## Security Considerations

- The MoA agent processes queries in the same secure environment as the base proxy
- No additional security permissions required beyond standard Ollama access
- Input sanitization follows the same patterns as the base system

## Best Practices

### Model Selection
- Choose diverse models for better consensus outcomes
- Balance quality vs. performance requirements
- Regularly update model lists based on availability and performance

### Configuration Tuning
- Adjust timeouts based on typical response times
- Limit model count based on available resources
- Monitor performance and adjust accordingly

### Usage Patterns
- Use for complex queries where multiple perspectives improve quality
- Consider alternatives for simple queries where single-model responses suffice
- Monitor resource usage during heavy MoA utilization