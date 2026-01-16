# Mixture of Agents (MoA) Plugin

## What is MoA?

The Mixture of Agents (MoA) plugin transforms how your AI applications generate responses by combining insights from multiple AI models. Instead of relying on a single model's perspective, MoA consults several models, evaluates their responses, and delivers the highest quality answer.

Think of it as getting multiple expert opinions on a complex question and choosing the best one, all happening instantly behind the scenes.

## Why Use MoA?

### Enhanced Response Quality
- **Multiple Perspectives**: Gets input from various AI models with different strengths
- **Quality Scoring**: Each response is evaluated by other models to identify the best answer
- **Consensus Building**: Combines multiple viewpoints for more comprehensive responses

### Business Benefits
- **Higher Accuracy**: Reduces chances of incorrect or low-quality responses
- **Better Problem Solving**: Complex queries benefit from diverse model approaches
- **Improved Reliability**: Less dependent on any single model's limitations

## How It Works

When you send a query to MoA, here's what happens behind the scenes:

1. **Parallel Processing**: Your question is sent to multiple AI models simultaneously
2. **Response Collection**: Each model generates its own answer independently
3. **Peer Review**: Models evaluate each other's responses using standardized criteria
4. **Best Answer Selection**: The highest-scoring response is delivered to you

This entire process typically happens in seconds, delivering superior results compared to single-model responses.

## Getting Started

### Prerequisites
- Ollama Smart Proxy installed and running
- Multiple Ollama models available (at least 2 recommended, 3+ ideal)

### Quick Setup
1. Ensure your desired models are available in Ollama:
   ```bash
   ollama list
   ```

2. Configure your models in `src/plugins/moa/config.json`:
   ```json
   {
     "moa_models": ["llama3.2", "mistral", "gemma2"],
     "timeout": 300,
     "max_models": 3
   }
   ```

### Usage
Simply prefix your queries with `/moa`:

```
/moa Explain quantum computing in simple terms
```

```
/moa What are the key factors affecting our Q4 sales forecast?
```

```
/moa Summarize the implications of new data privacy regulations for our business
```

## Configuration Options

### Model Selection Strategies

**For General Use**: Mix different model types (Llama, Mistral, Gemma)
```json
{
  "moa_models": ["llama3.2", "mistral", "gemma2"]
}
```

**For Speed**: Use smaller, faster models
```json
{
  "moa_models": ["phi3:mini", "gemma2:2b", "llama3.2:1b"]
}
```

**For Quality**: Use larger, more capable models
```json
{
  "moa_models": ["llama3.2:7b", "mistral:7b", "qwen2:7b"]
}
```

### Performance Tuning

**Faster Responses** (2-3 models):
- Better performance
- Good for routine queries
- Lower resource usage

**Higher Quality** (4-5 models):
- Superior results for complex queries
- Better for critical business decisions
- Higher resource usage

## When to Use MoA

### Ideal Use Cases
- **Complex Analysis**: Market research, competitive analysis, strategic planning
- **Critical Decisions**: Financial modeling, risk assessment, compliance questions
- **Creative Tasks**: Content generation, ideation, problem-solving
- **Technical Questions**: Architecture decisions, debugging, technical explanations

### When to Use Standard Models
- **Simple Queries**: Basic factual questions, quick checks
- **Real-time Applications**: Where speed is more critical than perfection
- **High-volume Requests**: When resource optimization is important

## Best Practices

### Model Selection
- Include diverse model architectures for broader perspectives
- Balance performance requirements with quality needs
- Regularly update your model mix based on availability and performance

### Query Optimization
- Ask clear, specific questions for best results
- Use MoA for queries where multiple perspectives add value
- Consider complexity vs. urgency trade-offs

### Resource Management
- Monitor resource usage during heavy MoA utilization
- Adjust model count based on your infrastructure capacity
- Consider using MoA selectively for high-value queries

## Examples

### Business Strategy
```
/moa What are the potential impacts of remote work trends on our real estate costs and employee productivity?
```

### Technical Decision Making
```
/moa Compare the pros and cons of microservices vs monolithic architecture for our e-commerce platform.
```

### Creative Problem Solving
```
/moa Generate innovative marketing campaign ideas for reaching Gen Z consumers in the sustainability space.
```

## Troubleshooting

### Common Issues

**Slow Responses**: 
- Reduce the number of models in configuration
- Check that all configured models are available in Ollama
- Increase timeout values if needed

**Generic Responses**:
- Try different model combinations
- Make your queries more specific
- Consider if a single model might be more appropriate

**Resource Constraints**:
- Limit the maximum number of models
- Use smaller models for less critical queries
- Monitor system resources during peak usage

## Performance Considerations

- **Response Time**: MoA responses typically take 2-5x longer than single-model queries
- **Resource Usage**: Consumes proportionally more computational resources
- **Cost**: May increase token/API usage depending on your model hosting setup

Plan your usage based on the importance and frequency of queries to optimize both quality and efficiency.