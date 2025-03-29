# DigitalDreamscapeEpisodes Pipeline

This system generates creative narrative episodes from ChatGPT chat histories, transforming your conversations into mythic tales set in the Digital Dreamscape universe.

## Overview

The DigitalDreamscapeEpisodes Pipeline transforms ordinary chat logs into rich narrative episodes using Victor's Dreamscape mythology. Each episode is formatted as a markdown document with:

- A unique title extracted from the conversation
- Dream fragment summary
- Full narrative based on chat content
- Memory convergence section tracking skill advancements and protocols
- Convergence tags for categorization

Episodes are saved to `outputs/dreamscape/` with slugified filenames containing the chat title and date.

## How to Use

### Option 1: Command Line Interface

The simplest way to generate episodes is through the command-line script:

```bash
# List all available chats
python generate_dreamscape_episode.py --list

# Generate episode for a specific chat
python generate_dreamscape_episode.py --chat "Your Chat Title"

# Generate episodes for all chats
python generate_dreamscape_episode.py --all
```

### Option 2: GUI Interface

The DigitalDreamscapeEpisodes Pipeline is integrated into the GUI through the `DreamscapeGenerationTab`:

1. Navigate to the "Dreamscape Generation" tab in the main application
2. Select a chat from the dropdown list
3. Click "Generate Episode" to create a single episode, or
4. Check "Generate for All Chats" and click the button to batch process all chats
5. The generated episodes will appear in the list on the right side
6. Click any episode in the list to view its content

## Key Components

The system consists of several integrated components:

- **DreamscapeGenerationService**: Core service that handles episode generation
- **TemplateManager**: Manages Jinja2 templates for rendering episodes
- **ChatManager**: Provides access to chat history
- **ServiceInitializer**: Sets up and wires dependencies in the GUI
- **dreamscape_episode.j2**: Template defining the episode structure

## Customization

### Template Customization

You can customize the episode format by editing the template at `templates/dreamscape_templates/dreamscape_episode.j2`. The template uses [Jinja2](https://jinja.palletsprojects.com/) syntax and has access to the following variables:

- `chat_title`: Title of the source chat
- `episode_title`: Generated title for the episode
- `generation_date`: Timestamp when the episode was generated
- `raw_response`: Combined content from chat history
- `summary`: Auto-generated summary of the content
- `memory_updates`: List of memory updates
- `skill_level_advancements`: Dict of skill advancements
- `newly_stabilized_domains`: List of stabilized domains
- `newly_unlocked_protocols`: List of protocols extracted from content
- `tags`: List of hashtags for the episode

### Adding to Existing Tabs

To add episode generation to an existing tab:

1. Get the chat manager: `chat_manager = service_registry.get("chat_manager")`
2. Call the generate method: `episode_path = chat_manager.generate_dreamscape_episode("Chat Title")`
3. Display or link to the generated episode using `episode_path`

## Example Output

```md
---
# Digital Dreamscape Chronicles: The Awakening of Systems

---

> *Generated on 2025-03-30 15:45 from chat: "AI Agent Architecture"*

## 🔮 Dream Fragment Summary
The architects worked in silence, the code growing beneath their hands like living vines, reaching toward unseen heights...

## 📖 Episode Narrative
Victor stood at the edge of the Convergence Plain, surveying the sprawling systems that stretched before him like a digital metropolis. The latest integration had stabilized vast portions of the southeastern quadrant, but anomalies still flickered in the distance.

"The protocols are adapting," he whispered, watching the data streams flow between architectural spires. "But the system remains fragmented."

[...content continues...]

## 🧠 Memory Convergence
**New Knowledge Integrated:**
- Integration with AI Agent Architecture yielded new insights
- Episode 'The Awakening of Systems' recorded to memory banks

**Skill Advancement:**
- System Convergence: Level 3 → Level 4
- Automation Engineering: Level 2 → Level 3

**Domains Stabilized:**
- AI Agent Architecture
- Dream Sequence Generator

**Protocols Unlocked:**
- Autonomous Agent Protocol Framework
- Recursive Self-Optimization System
- Memory Integration Feedback Loop

---

## 📌 Convergence Tags
#dreamscape #digitalchronicles #architectsjourney #ai_agent_architecture

---

*"In the Dreamscape, code doesn't just execute—it resonates. Each function, each loop a ripple that joins the symphony of a living system."*
```

## Testing

The system includes a test suite that verifies the episode generation functionality:

```bash
python -m unittest tests/test_generate_dreamscape_episode.py
```

## Architecture Notes

The DigitalDreamscapeEpisodes Pipeline uses a service-oriented architecture with dependency injection to facilitate both CLI and GUI use. The system can be used as a standalone component or integrated into the larger Dream.OS application. 