# Hybrid Context System Architecture

The DigitalDreamscapeEpisodes system uses a hybrid approach to context management, combining LLM-based semantic memory with structured data and web-scraped content.

## System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Context Sources                              │
└───────────┬─────────────────┬──────────────────┬────────────────┘
            │                 │                  │
            ▼                 ▼                  ▼
┌───────────────────┐ ┌─────────────────┐ ┌────────────────────┐
│ Web-Scraped       │ │ Episode Chain   │ │ Semantic Memory    │
│ Content           │ │ JSON            │ │ (LLM-based)        │
│                   │ │                 │ │                    │
│ • HTML parsing    │ │ • Quest status  │ │ • Conversation     │
│ • DOM extraction  │ │ • Episode log   │ │   history          │
│ • UI elements     │ │ • Location info │ │ • Thematic patterns│
└───────┬───────────┘ └────────┬────────┘ └──────────┬─────────┘
        │                      │                     │
        │                      │                     │
        ▼                      ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                 PromptContextSynthesizer                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Synthesis Process                                       │   │
│  │                                                         │   │
│  │ 1. Load multiple context sources                        │   │
│  │ 2. Analyze & prioritize relevant information            │   │
│  │ 3. Generate semantic summary using GPT-4o               │   │
│  │ 4. Structure context into template sections             │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                  DreamscapeGenerationService                     │
│                                                                 │
│  • Receives unified context from synthesizer                    │
│  • Generates coherent episode with narrative continuity         │
│  • Updates memory systems with new episode data                 │
│  • Extracts new themes, quests, characters                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Generated Episode                          │
│                                                                 │
│  • Contains "Previously in the Dreamscape" section              │
│  • References ongoing quests                                    │
│  • Maintains character continuity                               │
│  • Evolves narrative setting                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Context Source Details

### 1. Web-Scraped Content
- **Implementation**: Selenium-based web scraper
- **Benefits**: Real-time, UI-based context extraction
- **Use Cases**: When chat history needs to be accessed directly from the UI
- **Limitations**: Dependent on UI stability, slower than memory-based approaches

### 2. Structured Episode Chain
- **Implementation**: JSON-based persistent storage (`episode_chain.json`)
- **Benefits**: Explicit tracking of narrative elements
- **Key Elements**: 
  - Episode count and sequence
  - Ongoing and completed quests
  - Current location and emotional state
  - Character relationships

### 3. Semantic Memory (LLM-based)
- **Implementation**: GPT-4o processing of conversation history
- **Benefits**: Can extract implicit themes and connections
- **Key Capabilities**:
  - Identify recurring themes across conversations
  - Understand character development and arc progression
  - Generate coherent summaries of past episodes

## Context Synthesis Process

The `PromptContextSynthesizer` performs the following steps:

1. **Load Context Sources**:
   - Loads structured data from JSON files
   - Retrieves web-scraped content if available
   - Processes conversation history

2. **Context Prioritization**:
   - Recent episodes prioritized over older ones
   - Ongoing quests given prominence
   - Current emotional states and locations preserved

3. **Semantic Processing**:
   - LLM determines most relevant context elements
   - Generates a cohesive narrative thread
   - Creates a template-ready context block

4. **Template Integration**:
   - Context is structured for markdown template insertion
   - "Previously in the Dreamscape" section created
   - Quest status updated with progress info

## Configuration Options

The system can be configured to prioritize different context sources:

```json
{
  "context_weights": {
    "web_scraping": 0.3,
    "episode_chain": 0.3,
    "semantic_memory": 0.4
  },
  "context_max_episodes": 3,
  "context_max_quests": 5
}
```

## Benefits of the Hybrid Approach

1. **Redundancy**: If one source fails, others provide backup context
2. **Complementary Strengths**: Structured data for clarity, LLM for creativity
3. **Adaptive**: Can prioritize different sources based on availability
4. **Evolution**: System improves as episode chain grows and patterns emerge

The hybrid context approach ensures that each generated episode maintains narrative continuity while allowing for creative evolution of the dreamscape world. 