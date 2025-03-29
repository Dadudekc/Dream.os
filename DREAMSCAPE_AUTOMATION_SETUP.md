# Dreamscape Automation Setup Guide

This guide explains how to set up the automated Dreamscape Episode generation pipeline to transform your chat histories into narrative episodes on a regular schedule, with dynamic episode chaining for ongoing narrative continuity.

## Prerequisites

- Python 3.7+
- Dream.OS project with restored DigitalDreamscapeEpisodes pipeline
- Administrator access (for setting up scheduled tasks)

## Files Overview

The automation system consists of the following components:

- **dreamscape_automation.py**: Main script that processes chats into episodes
- **scheduled_dreamscape.py**: Wrapper script for scheduled execution
- **templates/dreamscape_templates/dreamscape_episode.j2**: Template for episode generation
- **core/services/dreamscape_generator_service.py**: Service that handles episode generation
- **core/services/dreamscape_episode_chain.py**: Service that manages episode continuity and memory
- **core/scraping/web_chat_scraper.py**: Service that scrapes chats directly from the ChatGPT UI
- **memory/dreamscape_memory.json**: Memory file for persistent narrative elements
- **memory/episode_chain.json**: Episode chain tracking for narrative continuity
- **dreamscape_schedule_status.json**: Status file tracking execution history
- **processed_dreamscape_chats.json**: Archive of processed chats

## Installation Steps

1. Ensure the prerequisites are met:
   ```bash
   # Check Python version
   python --version
   
   # Install required dependencies
   pip install selenium webdriver_manager jinja2
   ```

2. Set up the template directory and memory storage:
   ```bash
   mkdir -p templates/dreamscape_templates
   mkdir -p memory
   ```

3. Ensure the DigitalDreamscapeEpisodes components are correctly installed:
   - The `generate_dreamscape_episode` method in `DreamscapeGenerationService`
   - The `get_chat_history` method in `ChatManager`
   - The `dreamscape_episode.j2` template
   - The `dreamscape_episode_chain.py` module for dynamic episode chaining
   - The `WebChatScraper` class for direct chat scraping

4. Test the automation script manually:
   ```bash
   # List available chats from memory
   python dreamscape_automation.py --list
   
   # List available chats directly from ChatGPT UI
   python dreamscape_automation.py --list --web
   
   # Test with a single chat from memory
   python dreamscape_automation.py --chat "Your Chat Title"
   
   # Test with a single chat from web scraping
   python dreamscape_automation.py --chat "Your Chat Title" --web
   
   # See current episode chain status
   python dreamscape_automation.py --status
   
   # Test the full automation from memory
   python dreamscape_automation.py --all
   
   # Process multiple episodes at once
   python dreamscape_automation.py --all --count 5
   
   # Test the full automation with web scraping
   python dreamscape_automation.py --all --web
   ```

## Dynamic Episode Chaining

The system now features **dynamic episode chaining** which enables:

1. **Narrative Continuity** - Each episode builds upon previous ones
2. **Memory Persistence** - Character development and ongoing storylines are preserved 
3. **Quest Tracking** - Track ongoing and completed quests across episodes
4. **Progressive World-Building** - The world evolves naturally through cumulative episodes

### How Episode Chaining Works

When generating episodes:
1. The system extracts context from the last episode
2. This context is incorporated into new episodes
3. Generated episodes update both memory and the episode chain
4. Each new episode includes elements from past episodes

### Viewing Chain Status

Check the status of the episode chain to see narrative progress:

```bash
python dreamscape_automation.py --status
```

This will display statistics such as:
- Total number of episodes generated
- Most recent episode title
- Current character location
- Active and completed quests
- Quest completion rate

## Setting Up Scheduled Execution

### Windows (Task Scheduler)

1. Open Task Scheduler (search for "Task Scheduler" in the Start menu)
2. Click "Create Basic Task..."
3. Enter a name (e.g., "Dreamscape Episode Generation") and description
4. Set the trigger (e.g., Daily at 2 AM)
5. Select "Start a program" for the action
6. In the "Program/script" field, enter the full path to your Python executable
7. In the "Add arguments" field, enter:
   ```
   full\path\to\scheduled_dreamscape.py --discord --web
   ```
   (Include `--web` to use web scraping or omit it to use memory)
8. In the "Start in" field, enter the full path to your project directory
9. Complete the wizard and check "Open the Properties dialog..." checkbox
10. In the Properties dialog, under the Settings tab:
    - Check "Run task as soon as possible after a scheduled start is missed"
    - Set "If the task is already running, then the following rule applies:" to "Stop the existing instance"

### macOS/Linux (cron)

1. Open the terminal
2. Edit your crontab:
   ```bash
   crontab -e
   ```
3. Add an entry to run the scheduled script (e.g., daily at 2 AM):
   ```
   0 2 * * * cd /path/to/your/project && /usr/bin/python3 scheduled_dreamscape.py --discord --web >> /path/to/your/project/logs/cron_dreamscape.log 2>&1
   ```
   (Include `--web` to use web scraping or omit it to use memory)
4. Save and exit (Ctrl+X, then Y in nano)

### Systemd Timer (Linux)

1. Create a service file:
   ```bash
   sudo nano /etc/systemd/system/dreamscape.service
   ```
2. Add the following content:
   ```
   [Unit]
   Description=Dreamscape Episode Generation Service
   After=network.target
   
   [Service]
   Type=oneshot
   User=your_username
   WorkingDirectory=/path/to/your/project
   ExecStart=/usr/bin/python3 /path/to/your/project/scheduled_dreamscape.py --discord --web
   
   [Install]
   WantedBy=multi-user.target
   ```
   (Include `--web` in ExecStart to use web scraping or omit it to use memory)
3. Create a timer file:
   ```bash
   sudo nano /etc/systemd/system/dreamscape.timer
   ```
4. Add the following content:
   ```
   [Unit]
   Description=Run Dreamscape Episode Generation Daily
   
   [Timer]
   OnCalendar=*-*-* 02:00:00
   Persistent=true
   
   [Install]
   WantedBy=timers.target
   ```
5. Enable and start the timer:
   ```bash
   sudo systemctl enable dreamscape.timer
   sudo systemctl start dreamscape.timer
   ```

## Advanced Configuration

### Changing the Schedule Interval

The default minimum interval between runs is 12 hours. To change this:

```bash
# Run with a custom interval (in hours)
python scheduled_dreamscape.py --discord --interval 24
```

### Force Running Regardless of Interval

If you need to run the script regardless of the last execution time:

```bash
python scheduled_dreamscape.py --discord --force
```

### Force Processing Already Processed Chats

By default, the system skips chats that have already been processed:

```bash
# Force processing of all chats regardless of previous processing
python dreamscape_automation.py --all --force
```

### Processing Multiple Episodes at Once

Control how many episodes are generated in a single run:

```bash
# Generate up to 3 episodes from unprocessed chats
python dreamscape_automation.py --all --count 3
```

### Choosing Web Scraping vs Memory Source

The pipeline supports two methods of retrieving chat histories:

```bash
# Use memory file (default)
python scheduled_dreamscape.py --discord

# Use web scraping (scrapes ChatGPT UI directly)
python scheduled_dreamscape.py --discord --web
```

### Customizing Discord Notifications

Edit the `notify_discord` function in `scheduled_dreamscape.py` to customize the notification format.

### Changing Excluded Chats

Edit the `get_excluded_chats` function in `dreamscape_automation.py` to customize which chats to skip.

## Memory and Chain File Management

### Memory File Structure

The `memory/dreamscape_memory.json` file stores persistent narrative elements:

```json
{
  "protocols": ["Protocol names"],
  "quests": {
    "Quest Name": "active|completed"
  },
  "realms": ["Realm names"],
  "artifacts": ["Artifact names"],
  "characters": ["Character names"],
  "themes": ["Theme names"],
  "stabilized_domains": ["Domain names"]
}
```

### Episode Chain Structure

The `memory/episode_chain.json` file tracks the series of episodes:

```json
{
  "episode_count": 12,
  "last_episode": "Episode Title",
  "current_emotional_state": "Determined",
  "last_location": "The Nexus",
  "last_updated": "2023-07-15T10:15:30.123Z",
  "ongoing_quests": ["Quest 1", "Quest 2"],
  "completed_quests": ["Quest 3", "Quest 4"],
  "episodes": [
    {
      "id": 1,
      "timestamp": "2023-07-01T08:15:30.123Z",
      "filename": "episode_filename.md",
      "title": "Episode Title",
      "summary": "Brief summary",
      "location": "Location",
      "emotional_state": "Emotional State",
      "ongoing_quests": ["Quests started"],
      "completed_quests": ["Quests completed"]
    }
  ]
}
```

You can manually edit these files to influence the narrative direction if needed.

## Troubleshooting

### Script Runs But No Episodes Are Generated

1. Check the log files in the project directory
2. Verify the chat manager can access your chat history
3. Ensure the template exists and is correctly formatted
4. Try running the script with the `--discord` flag to see Discord error messages
5. If using `--web` mode, ensure you have a valid ChatGPT login session

### Episode Chain Not Updating

1. Check permissions on the memory directory
2. Verify that the memory and chain files can be created/updated
3. Run with `--status` to see the current chain status
4. Check the log for errors related to episode chain updates

### Web Scraping Mode Issues

1. Ensure the ChatGPT profile is correctly configured in your browser
2. Verify that your cookies are valid by running with --web --list to see if chats are detected
3. Check if there are any JavaScript errors in the browser console
4. Try increasing the wait timeouts in WebChatScraper if content loading is slow

### Scheduled Task Doesn't Run

1. Check the task's history in Task Scheduler (Windows) or journal logs (Linux)
2. Ensure the paths to Python and the script are correct
3. Verify that the user account has permissions to run the task
4. Check if the minimum interval has passed since the last run

### Discord Integration Not Working

1. Verify that your Discord token is set correctly
2. Ensure the bot has permissions to post in the channel
3. Check if the Discord service is available in your service registry

## Monitoring and Maintenance

- **Status File**: Check `dreamscape_schedule_status.json` for the last run time and status
- **Log Files**: Monitor `dreamscape_automation.log` for execution details
- **Archive**: Review `processed_dreamscape_chats.json` for a history of processed chats
- **Episode Chain**: Check `memory/episode_chain.json` for narrative progression
- **Memory File**: Review `memory/dreamscape_memory.json` for persistent story elements

For manual inspection of generated episodes, check the files in the `dreamscape/` directory (or the configured output directory).

## Support

If you encounter issues with the automated Dreamscape Episode generation, please:

1. Check the log files for specific error messages
2. Verify that all components are correctly installed
3. Ensure your chat history is accessible
4. Try running the script with the `--force` flag to bypass interval restrictions

## Additional Features

- **Template Customization**: Edit `templates/dreamscape_templates/dreamscape_episode.j2` to change the episode format
- **Discord Integration**: The system automatically posts generated episodes to Discord if the `--discord` flag is set
- **Exclusion Lists**: Chats can be excluded from processing based on their titles
- **Web Scraping**: The system can retrieve chat histories directly from the ChatGPT web interface when the `--web` flag is set 
- **Dynamic Chaining**: Episodes build upon each other, creating an evolving narrative universe
- **Memory Persistence**: Character development and world-building elements persist across episodes 