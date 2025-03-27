# DreamscapeGenerationTab Migration Guide

This guide helps you migrate from the legacy `DreamscapeGenerationTab` to the new modular implementation.

## Overview

The new `DreamscapeGenerationTab` implementation provides:
- ✅ Full dependency injection for all services
- ✅ Clean integration with `DreamscapeEpisodeGenerator`
- ✅ Async episode generation using `EpisodeGenerator.generate_episodes(...)`
- ✅ UI parity: episode list, template previews, logging, context memory, and Discord sharing
- ✅ Slot-based architecture with `@asyncSlot()` for smooth UI threading

## Migration Steps

### 1. Update Your Imports

Replace old imports:
```python
from archive.gui_old.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab
```

With new imports:
```python
from interfaces.pyqt.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab
```

### 2. Update Service Initialization

The new tab supports both direct service injection and UI logic-based initialization:

```python
# Option 1: Direct Service Injection
tab = DreamscapeGenerationTab(
    prompt_manager=prompt_manager,
    chat_manager=chat_manager,
    response_handler=response_handler,
    memory_manager=memory_manager,
    discord_manager=discord_manager,
    config_manager=config_manager,
    logger=logger
)

# Option 2: UI Logic-based Initialization
tab = DreamscapeGenerationTab(
    ui_logic=ui_logic_controller,
    config_manager=config_manager,
    logger=logger
)
```

### 3. Update Event Handlers

The new implementation uses async slots for better UI responsiveness:

```python
# Old way:
@pyqtSlot()
def on_generate_clicked(self):
    threading.Thread(target=self.generate_episodes).start()

# New way:
@asyncSlot()
async def on_generate_clicked(self):
    await self.episode_generator.generate_episodes()
```

### 4. Update Template Management

The new implementation uses the `TemplateManager` for better template organization:

```python
# Old way:
self.load_template("default_template.txt")

# New way:
template = self.template_manager.get_template("dreamscape/default")
self.context_manager.apply_template(template)
```

### 5. Update Episode Generation

The new implementation provides more control over episode generation:

```python
# Old way:
self.generate_dreamscape_episodes(output_dir="outputs")

# New way:
await self.episode_generator.generate_episodes(
    output_dir="outputs",
    template=template,
    context=self.context_manager.get_context(),
    options={
        "num_episodes": 5,
        "max_tokens": 2048,
        "temperature": 0.7
    }
)
```

### 6. Update UI Access

The new implementation uses the `UIManager` for centralized UI control:

```python
# Old way:
self.output_display.append("Message")

# New way:
self.ui_manager.log_message("Message")
```

## Testing Migration

1. Run the migration test suite:
```bash
python -m pytest tests/test_dreamscape_tab_migration.py
```

2. Verify feature parity:
```python
# In your test environment:
assert hasattr(new_tab, 'generate_dreamscape_episodes')
assert hasattr(new_tab, 'refresh_episode_list')
assert hasattr(new_tab, 'send_context_to_chatgpt')
```

## Cleanup

After successful migration:

```bash
# Remove old implementation
git rm archive/gui_old/tabs/DreamscapeGenerationTab.py

# Commit changes
git commit -m "Removed legacy DreamscapeGenerationTab in favor of new modular interface"
```

## New Features

The new implementation adds several enhancements:

1. **Episode Metadata Caching**
```python
# Cache episode metadata
await self.episode_generator.cache_episode_metadata(episode)

# Display cached metadata
metadata = self.episode_generator.get_cached_metadata(episode_id)
self.ui_manager.display_episode_metadata(metadata)
```

2. **Integration with AgentDispatcher**
```python
# Schedule automated episode generation
self.dispatcher.schedule_task(
    task_type="dreamscape_generation",
    interval="daily",
    options={
        "template": "daily_reflection",
        "num_episodes": 3
    }
)
```

3. **Real-time Discord Feedback**
```python
# Enable real-time Discord updates
self.discord_manager.enable_realtime_updates(
    webhook_url="your_webhook_url",
    update_interval=30  # seconds
)
```

## Support

If you encounter any issues during migration:
1. Check the test suite output for specific failures
2. Review the migration steps above
3. File an issue with the tag `migration-support` if needed

## Rollback

If you need to rollback:
1. Restore the old implementation from git history
2. Update your imports back to the old path
3. Remove any async/await usage added during migration 