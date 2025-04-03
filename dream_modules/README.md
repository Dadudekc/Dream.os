# Dream Modules

A collection of reusable modules for Discord bots and RPG systems. These modules are designed to be easily integrated into existing applications, with a focus on dependency injection and clean interfaces.

## Modules

### Core

- **Module Interfaces**: Base interfaces for all modules, providing common methods for initialization, shutdown, and status reporting.
- **Service Container**: A dependency injection container for managing service instances and dependencies.

### Character

- **Character Model**: A standalone character model for RPG systems.
- **Character Manager**: A service for managing characters, including creation, retrieval, updating, and deletion.

### Clan

- **Clan Model**: A standalone clan model for RPG systems.
- **Clan Manager**: A service for managing clan data, including retrieval and updating clan information.

### Discord

- **Character Commands**: Discord commands for character management, integrating with the character and clan services.

## Getting Started

### Installation

Copy the `dream_modules` directory to your project.

### Basic Usage

Here's a simple example of how to integrate these modules into a Discord bot:

```python
import discord
from discord.ext import commands
import os
import logging

# Import dream modules
from dream_modules.factory import setup_rpg_systems, shutdown_all_systems

# Set up logging
logging.basicConfig(level=logging.INFO)

# Create bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Configuration
config = {
    "character": {
        "data_dir": "data/characters",
        "auto_save": True,
    },
    "clan": {
        "data_dir": "data/clans",
        "clans_file": "clans.json",
    },
    "commands": {
        "role_management": {
            "enabled": True,
            "level_roles": {
                5: "Genin",
                10: "Chunin",
                20: "Jonin",
            }
        }
    }
}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    
    # Set up RPG systems
    systems = setup_rpg_systems(bot, config)
    
    # Sync commands
    await bot.tree.sync()
    print('Commands synced')

@bot.event
async def on_close():
    # Shutdown all systems
    shutdown_all_systems()
    print('Systems shutdown complete')

# Run bot
bot.run(os.getenv('DISCORD_TOKEN'))
```

### Advanced Usage

You can also create and configure each system individually:

```python
from dream_modules.factory import (
    create_character_system,
    create_clan_system,
    create_character_commands
)

# Create character system
character_config = {
    "data_dir": "data/characters",
    "auto_save": True,
}
character_system = create_character_system(character_config)

# Create clan system
clan_config = {
    "data_dir": "data/clans",
    "clans_file": "clans.json",
}
clan_system = create_clan_system(clan_config)

# Create character commands
commands_config = {
    "role_management": {
        "enabled": True,
        "level_roles": {
            5: "Genin",
            10: "Chunin",
            20: "Jonin",
        }
    }
}
character_commands = create_character_commands(bot, commands_config)
```

## Customization

### Extending Modules

You can extend the existing modules by subclassing them:

```python
from dream_modules.modules.character.character_model import Character

class ExtendedCharacter(Character):
    """Extended character model with additional attributes."""
    
    def __init__(self, name, clan="Civilian", **kwargs):
        super().__init__(name, clan, **kwargs)
        self.custom_attribute = kwargs.get('custom_attribute', '')
    
    def custom_method(self):
        return f"{self.name} is using a custom method!"
```

### Creating Custom Commands

You can create custom Discord commands that integrate with the existing systems:

```python
@bot.tree.command(name="train", description="Train your character")
async def train(interaction: discord.Interaction, skill: str):
    """Train a skill to earn experience."""
    # Get character system from container
    from dream_modules.core.service_container import get_container
    character_system = get_container().get("character_manager")
    
    # Get character
    character = character_system.get_character(str(interaction.user.id))
    if not character:
        await interaction.response.send_message("You don't have a character yet! Use `/create` to make one.")
        return
    
    # Add experience
    character.add_exp(10)
    
    # Save character
    character_system.save_character(str(interaction.user.id), character)
    
    await interaction.response.send_message(f"You trained {skill} and gained 10 XP!")
```

## Contributing

Feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 