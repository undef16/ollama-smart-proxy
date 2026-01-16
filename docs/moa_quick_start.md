# MoA Agent Quick Start Guide

## Prerequisites

- Ollama Smart Proxy installed and running
- Multiple Ollama models available (recommended: at least 2 different models)
- Basic understanding of the proxy's operation

## Setup

### 1. Configure Models

The MoA agent comes with default configuration in `src/plugins/moa/config.json`. You can either:

**Option A: Modify the config file directly**
```json
{
  "moa_models": ["gemma3:1b", "gemma3:4b", "gemma3:12b"],
  "timeout": 300,
  "max_models": 3,
  "prompts": {
    "ranking_prompt": "You are evaluating the model's response to the following question:\n\nQuestion: {query}\n\nResponse: {previous_response}\n\nYour task is to evaluate this response and return a score from 0 to 1, where 0 means the response is completely inadequate and 1 means the response is perfect.\n\nProvide your evaluation as a ONLY JSON object with the key 'score' containing the ONLY numerical value.\n\nExample: {\"score\": 0.75}",
    "batch_ranking_prompt": "You are evaluating multiple model responses to the following question:\n\nQuestion: {query}\n\nResponses to evaluate:\n{responses}\n\nYour task is to evaluate each response and return scores from 0 to 1, where 0 means the response is completely inadequate and 1 means the response is perfect.\n\nProvide your evaluation as a JSON array ONLY with objects containing 'response_id' and 'score' fields ONLY without any additional text or score describe.\n\nExample: [{\"response_id\": 0, \"score\": 0.75}, {\"response_id\": 1, \"score\": 0.85}]"
  }
}
```

**Option B: Use environment variables** (these override config file settings)
```bash
export OLLAMA_MOA_MODELS="gemma3:1b,llama3.2,mistral,phi3"
export OLLAMA_MOA_TIMEOUT=300
export OLLAMA_MOA_MAX_MODELS=4
```

### 2. Verify Model Availability

Ensure all configured models are available in Ollama:
```bash
ollama list
```

If needed, pull required models:
```bash
ollama pull gemma3:1b
ollama pull llama3.2
ollama pull mistral
```

## Usage

### Basic Usage

To use the MoA agent, send a query prefixed with `/moa`:

**Using curl:**
```bash
curl -X POST http://localhost:11555/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2",
    "messages": [
      {"role": "user", "content": "/moa Explain quantum computing in simple terms"}
    ]
  }'
```

**Using the proxy's interface or client:**
```
/moa What are the main differences between Python and JavaScript?
```

### Expected Response

The MoA agent will:
1. Query all configured models in parallel (Stage 1)
2. Have models rank each other's responses (Stage 2)
3. Select the highest-scoring response as the final answer
4. Return the response in standard format

## Configuration Options

### Model Selection

Choose models that offer diverse perspectives for better consensus:
- Mix of instruction-following and creative models
- Different architectures (Llama, Mistral, Gemma, etc.)
- Varying sizes (small, medium, large)

### Performance Tuning

Adjust settings based on your needs:

**For faster responses:**
- Reduce the number of models (max_models: 2)
- Lower timeout values
- Use smaller, faster models

**For higher quality:**
- Increase the number of models (max_models: 4-5)
- Use diverse, high-quality models
- Allow longer timeout values

### Example Configurations

**Development/Testing:**
```json
{
  "moa_models": ["gemma3:1b", "phi3:mini"],
  "timeout": 120,
  "max_models": 2
}
```

**Production/Quality-focused:**
```json
{
  "moa_models": ["llama3.2:7b", "mistral:7b", "gemma2:7b", "qwen2:7b", "phi3:medium"],
  "timeout": 300,
  "max_models": 5
}
```

## Monitoring and Troubleshooting

### Checking Logs

Monitor the logs to see the MoA process in action:
- Stage 1: Response collection
- Stage 2: Peer ranking
- Any model failures or fallbacks

### Common Issues

**Issue**: Response takes too long
- **Solution**: Reduce model count or lower timeout values

**Issue**: MoA not activating
- **Solution**: Ensure query starts with `/moa` (case-sensitive)

**Issue**: Some models returning errors
- **Solution**: Verify model availability with `ollama list`

## Tips for Best Results

1. **Use for Complex Queries**: MoA works best for complex questions requiring multiple perspectives
2. **Monitor Resource Usage**: Multiple model queries consume more resources than single queries
3. **Iterate on Configuration**: Adjust model selection based on your specific use cases
4. **Balance Speed vs Quality**: More models provide better quality but take longer

## Next Steps

- Experiment with different model combinations
- Monitor the quality of MoA responses vs. single-model responses
- Adjust configuration based on performance and quality requirements
- Explore advanced configuration options for specialized use cases