<<<<<<< HEAD
# DigitalDreamscapeEpisodes

A system for generating interconnected dream-like narrative episodes from your chat interactions, providing a continuity-aware creative reflection of your conversations.

## Features

- 🧠 **Hybrid Context Synthesis** - Combines LLM-based semantic memory with structured episode data and web-scraped content for deeper narrative continuity
- 🔄 **Dynamic Episode Chaining** - Each episode builds on previous ones, maintaining character development, themes, and quests
- 🌌 **Automated Worldbuilding** - Consistent world elements persist across episodes through memory persistence
- 🤖 **Automated Generation** - Schedule regular episode creation from your chat history
- 🔔 **Discord Integration** - Share generated episodes to Discord with rich formatting and status updates
- 📊 **Chain Analysis** - Track narrative progression, quest completion, and emotional arcs

## System Architecture

The system consists of:

1. **Core Services**:
   - `DreamscapeGenerationService`: Handles episode creation with context awareness
   - `PromptContextSynthesizer`: Merges multiple context sources for coherent narratives
   - Memory persistence through `dreamscape_memory.json` and `episode_chain.json`

2. **Automation Tools**:
   - `dreamscape_automation.py`: Generate episodes from chat history with web scraping or memory
   - `scheduled_dreamscape.py`: Run generation on a schedule with smart context source selection

3. **Templates**:
   - Markdown-based episode templates with sections for previous context, quests, and summaries

## Memory System

The DigitalDreamscapeEpisodes system uses multiple memory layers:

### 1. Semantic Memory
LLM-based reasoning over previous episodes to extract themes, character development, and plot points.

### 2. Structured Memory
JSON-based persistent memory stores:
- `dreamscape_memory.json`: Long-term world elements (protocols, characters, quests, etc.)
- `episode_chain.json`: Episode sequence tracking and quest status
- `conversation_memory.json`: Chat-specific memories for context retrieval

### 3. Web-Scraped Context
When enabled, extracts conversation context directly from chat interfaces.

## Getting Started

### Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Configure settings in `config.json` (create from template if needed)

### Usage

#### Manual Generation

To generate episodes manually:

```
python dreamscape_automation.py --chat "Chat Title"
```

Options:
- `--web`: Use web scraping for retrieving chat history (vs. memory)
- `--discord`: Send the generated episode to Discord
- `--analysis`: Show detailed episode chain analysis

#### Scheduled Generation

To set up automated scheduled generation:

```
python scheduled_dreamscape.py --interval 6 --discord --continuous
```

Options:
- `--interval`: Hours between runs (default: 6)
- `--jitter`: Random minutes of jitter to add (default: 30)
- `--continuous`: Run as a daemon, continuously checking schedule
- `--status`: Show current status and exit

## Understanding Episode Chain Structure

Each episode connects to previous ones through:

1. **Direct References** - "Previously in the Dreamscape" section
2. **Quest Continuity** - Ongoing quests persist between episodes
3. **Character Development** - Emotional arcs connect across episodes
4. **Location Progression** - Movement through the dreamscape world

## Integration Options

The system can be integrated with:

- Discord for sharing episodes and status updates
- Chat interfaces for retrieving conversation context
- Custom applications through the included Python API

## Customization

You can customize the system by:

1. Modifying episode templates in the `templates/dreamscape_templates` directory
2. Adjusting LLM prompt parameters in `config.json`
3. Creating custom scripts that utilize the `DreamscapeGenerationService` class

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
=======
# Dream.OS
>>>>>>> 201c4bdc9956acf8e03287d5c95a997199e222bf
