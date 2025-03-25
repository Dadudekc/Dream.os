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

## Requirements

- Python 3.8+
- Selenium with Chrome WebDriver
- Discord.py (optional, for Discord integration)
- PyYAML

## License

MIT 