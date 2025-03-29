# Hybrid Context System

The DigitalDreamscapeEpisodes system uses a sophisticated hybrid approach to context management, combining multiple sources for optimal narrative continuity.

## Overview

The hybrid context system is centered around the `PromptContextSynthesizer` class, which intelligently merges context from:

1. **Structured Memory** (JSON-based persistent storage)
2. **Semantic Memory** (LLM-based reasoning and understanding)
3. **Web-Scraped Content** (UI-based extraction)

Each context source receives a confidence score that, combined with configurable weights, determines its influence on the final synthesized context.

## Key Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Web Interface   │    │ Memory Files     │    │ Chat History    │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PromptContextSynthesizer                      │
├─────────────────────────────────────────────────────────────────┤
│ • Loads context from multiple sources                           │
│ • Assigns confidence scores to each source                      │
│ • Applies configurable weights                                  │
│ • Resolves conflicts between sources                            │
│ • Generates coherent semantic summary                           │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Synthesized Context Object                     │
├─────────────────────────────────────────────────────────────────┤
│ • Persistent world elements                                      │
│ • Narrative continuity factors                                   │
│ • Current conversation insights                                  │
│ • Quality metrics and source contributions                       │
└─────────────────────────────────────────────────────────────────┘
```

## Usage

### Basic Usage

```python
from core.services.prompt_context_synthesizer import PromptContextSynthesizer

# Initialize the synthesizer
synthesizer = PromptContextSynthesizer()

# Synthesize context using chat history
context = synthesizer.synthesize_context(
    chat_title="My Chat",
    chat_history=["Message 1", "Message 2", "Message 3"]
)
```

### Configuring Weights

You can configure the relative importance of different context sources:

```python
context = synthesizer.synthesize_context(
    chat_title="My Chat",
    chat_history=chat_history,
    config={
        "context_weights": {
            "web_scraping": 0.3,
            "episode_chain": 0.4,
            "semantic_memory": 0.3
        }
    }
)
```

### Combining Multiple Sources

The system excels when combining multiple sources:

```python
context = synthesizer.synthesize_context(
    chat_title="My Chat",
    chat_history=chat_history,
    web_scraped_content=web_content,
    additional_context={
        "user_preference": "Technical language",
        "semantic_themes": ["automation", "AI systems"]
    }
)
```

## Configuration Options

The context synthesis system accepts a configuration dictionary with the following options:

```json
{
  "context_weights": {
    "web_scraping": 0.3,
    "episode_chain": 0.4,
    "semantic_memory": 0.3
  },
  "context_max_episodes": 3,
  "context_max_quests": 5,
  "max_recent_messages": 5,
  "use_llm_summarization": false,
  "source_thresholds": {
    "episode_chain": 0.3,
    "semantic_memory": 0.4,
    "web_content": 0.25
  }
}
```

## Context Quality Metrics

Each synthesized context includes quality metrics:

```python
context["context_quality"] = {
    "contributions": {
        "web_content": 0.65,
        "episode_chain": 0.78,
        "semantic_memory": 0.45
    },
    "overall_confidence": 0.63,
    "sources_used": ["web_content", "episode_chain", "semantic_memory"]
}
```

## Memory Updates

The system can update memory files with insights from the synthesized context:

```python
synthesizer.update_memory_with_synthesized_context(context)
```

This creates a feedback loop where each context synthesis improves future contexts.

## When To Use Different Context Sources

| Context Source | Best For | Example Scenario |
|----------------|----------|------------------|
| Web Scraping | UI-dependent interactions | When you need to extract content directly from ChatGPT UI |
| Episode Chain | Narrative continuity | When building a storyline across multiple episodes |
| Semantic Memory | Thematic understanding | When needing to understand themes and concepts discussed |
| Chat History | Immediate context | When direct access to recent messages is important |

## Integration with DreamscapeGenerationService

The `PromptContextSynthesizer` is designed to work directly with the `DreamscapeGenerationService`:

```python
from core.services.dreamscape_generator_service import DreamscapeGenerationService
from core.services.prompt_context_synthesizer import PromptContextSynthesizer

# Initialize services
synthesizer = PromptContextSynthesizer()
dreamscape_service = DreamscapeGenerationService()

# Generate an episode using synthesized context
context = synthesizer.synthesize_context(
    chat_title="My Chat",
    chat_history=chat_history
)

episode = dreamscape_service.render_episode("dreamscape_template.j2", context)
```

## Best Practices

1. **Combine Multiple Sources**: For best results, provide both structured data and LLM-based context
2. **Configure Weights**: Adjust weights based on your specific use case
3. **Update Memory**: Always update memory with new contexts to improve future syntheses
4. **Validate Source Confidence**: Check confidence scores to ensure quality
5. **LLM Summarization**: For more nuanced understanding, enable LLM summarization in the config 