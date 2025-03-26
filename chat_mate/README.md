# Digital Dreamscape System

Automated content generation and analysis system for personal knowledge management, devlogs, and strategy development.

## Overview

The Digital Dreamscape System is a suite of tools for automating content workflows, including:

- ChatGPT conversation processing with custom prompts
- Automatic generation of devlogs from chat histories
- Content idea extraction and strategy analysis
- Persistent memory system for knowledge management
- Flexible configuration system

## Project Structure

```
project_root/
├── core/                   # Core business logic
│   ├── agents/             # Service and API agent implementations
│   │   └── chat_agent.py   # ChatGPT automation agent
│   ├── memory/             # Memory and storage
│   │   └── memory_manager.py  # Episodic memory storage
│   └── utils/              # Utility functions
│       ├── config_manager.py  # Configuration management
│       └── setup_environment.py  # Environment setup
├── config/                 # Configuration files
├── data/                   # Data storage
│   └── memory/             # Memory storage
├── logs/                   # Log files
├── outputs/                # Generated outputs
└── main.py                 # Main entry point
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/digital-dreamscape.git
   cd digital-dreamscape
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

The system can be run in several modes:

### Process ChatGPT Chats

Process your ChatGPT conversations with various prompt templates:

```bash
python main.py --process-chats
```

Options:
- `--max-chats N`: Process at most N chats
- `--prompt-types devlog content_ideas market_analysis`: Process only specific prompt types

### View Memory

View information from the persistent memory system:

```bash
python main.py --memory
```

Options:
- `--recent`: Show recent episodes
- `--recent-count N`: Show N recent episodes
- `--show-content`: Show content previews
- `--stats-only`: Show only statistics

### Interactive Chat Interface

Start an interactive chat interface (experimental):

```bash
python main.py --chat
```

## Development

Development mode limits the number of chats processed for testing:

```bash
python main.py --process-chats --dev
```

Configuration:
- Base configuration is in `config/base.yaml`
- Environment-specific overrides in `config/dev.yaml`, `config/prod.yaml`, etc.

## Dreamscape Content Generation

The Dreamscape module generates creative narrative episodes from your ChatGPT conversations:

```bash
python scripts/run_dreamscape.py
```

Options:
- `--headless`: Run in headless browser mode (no UI)
- `--skip-discord`: Skip posting results to Discord
- `--config FILE`: Specify a custom config file

Each episode is saved to the `outputs/dreamscape` directory with timestamp and chat title. The system will:
1. Navigate to all your ChatGPT chats
2. Skip excluded chats (configurable)
3. Send the Dreamscape prompt to each chat
4. Capture the response and save it as an episode
5. Optionally post to Discord if configured

The episodes reimagine technical work as mythic narrative, perfect for creative content or social media.

### Dreamscape Context Automation

The system now includes context memory that carries narrative themes between episodes:

```bash
python scripts/update_dreamscape_context.py
```

This feature allows:
- **Automatic context sharing**: Send current narrative context to ChatGPT
- **Episode continuity tracking**: Automatically numbers episodes sequentially
- **Last episode summaries**: New chats receive summaries of previous episodes
- **Scheduled updates**: Configure regular updates (daily, weekly, etc.)
- **Theme extraction**: The system analyzes episodes and extracts key themes
- **Memory system**: Previously generated episodes influence future ones

You can schedule context updates to run automatically:

```bash
# Add to crontab (Linux/Mac)
0 9 * * * cd /path/to/project && ./scripts/update_dreamscape_context.sh

# Add to Task Scheduler (Windows)
# - Program: C:\Windows\System32\cmd.exe
# - Arguments: /c "D:\path\to\project\scripts\update_dreamscape_context.bat"
```

The enhanced context system now:
1. Tracks episode numbers automatically
2. Sends previous episode summaries at the start of each new chat
3. Intelligently shares the narrative context across all chats
4. Maintains the evolution of characters, themes, and realms

The context memory system ensures a cohesive narrative across all dreamscape episodes, creating a rich, evolving mythology for your technical work.

## Requirements

- Python 3.8+
- Selenium with Chrome WebDriver
- Discord.py (optional, for Discord integration)
- PyYAML

## License

MIT 