"""Example Discord bot using dream_modules.

This is an example of how to use the dream_modules package
to create a Discord bot with character and clan management features.
"""
import os
import discord
from discord.ext import commands
import logging
import asyncio
import json

# Import dream modules
from dream_modules.factory import setup_rpg_systems, shutdown_all_systems


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Bot configuration
BOT_CONFIG = {
    "command_prefix": "!",
    "description": "RPG Bot with character and clan management",
    "intents": discord.Intents.default(),
}

# Dream modules configuration
MODULES_CONFIG = {
    "character": {
        "data_dir": "data/characters",
        "auto_save": True,
        "backup_enabled": True,
        "backup_interval": 3600,  # 1 hour
        "backup_dir": "data/backups/characters",
    },
    "clan": {
        "data_dir": "data/clans",
        "clans_file": "clans.json",
        "auto_save": True,
    },
    "commands": {
        "enable_cooldowns": True,
        "create_cooldown": 300,  # 5 minutes
        "profile_cooldown": 10,  # 10 seconds
        "delete_cooldown": 3600,  # 1 hour
        "role_management": {
            "enabled": True,
            "level_roles": {
                5: "Genin",
                10: "Chunin",
                20: "Jonin",
                30: "ANBU",
                50: "Kage"
            },
            "clan_roles": True,
            "specialization_roles": {
                "Taijutsu": "Taijutsu Specialist",
                "Ninjutsu": "Ninjutsu Specialist",
                "Genjutsu": "Genjutsu Specialist"
            }
        }
    }
}


# Set up intents
BOT_CONFIG["intents"].message_content = True
BOT_CONFIG["intents"].members = True


# Create bot
bot = commands.Bot(
    command_prefix=BOT_CONFIG["command_prefix"],
    description=BOT_CONFIG["description"],
    intents=BOT_CONFIG["intents"]
)


# Ensure data directories exist
def setup_directories():
    """Create necessary data directories."""
    os.makedirs(MODULES_CONFIG["character"]["data_dir"], exist_ok=True)
    os.makedirs(MODULES_CONFIG["character"]["backup_dir"], exist_ok=True)
    os.makedirs(MODULES_CONFIG["clan"]["data_dir"], exist_ok=True)


# Create example clan data
def create_example_clans():
    """Create example clan data if no clan data exists."""
    clans_file = os.path.join(MODULES_CONFIG["clan"]["data_dir"], MODULES_CONFIG["clan"]["clans_file"])
    
    # Skip if file already exists
    if os.path.exists(clans_file):
        return
    
    # Example clan data
    clans = {
        "Uchiha": {
            "name": "Uchiha",
            "rarity": "Legendary",
            "lore": "A clan known for their powerful Sharingan and fire techniques.",
            "special_ability": "Sharingan: Enhances perception and allows copying jutsu",
            "stat_bonuses": {
                "ninjutsu": 5,
                "perception": 3,
                "intelligence": 2
            },
            "starting_jutsu": ["Fireball Jutsu", "Phoenix Flower Jutsu"],
            "color": 16711680  # Red
        },
        "Hyuga": {
            "name": "Hyuga",
            "rarity": "Epic",
            "lore": "A noble clan with the Byakugan kekkei genkai.",
            "special_ability": "Byakugan: See through objects and detect chakra points",
            "stat_bonuses": {
                "taijutsu": 5,
                "perception": 5
            },
            "starting_jutsu": ["Gentle Fist", "8 Trigrams 32 Palms"],
            "color": 14408667  # Light purple
        },
        "Nara": {
            "name": "Nara",
            "rarity": "Rare",
            "lore": "A clan known for their shadow manipulation techniques and intelligence.",
            "special_ability": "Shadow Manipulation: Control shadows for various uses",
            "stat_bonuses": {
                "intelligence": 5,
                "chakra_control": 3
            },
            "starting_jutsu": ["Shadow Possession Jutsu", "Shadow Strangling Jutsu"],
            "color": 7170304  # Dark green
        },
        "Civilian": {
            "name": "Civilian",
            "rarity": "Common",
            "lore": "Common citizens with no special clan abilities.",
            "special_ability": "Determined Spirit: Work hard to succeed through perseverance",
            "stat_bonuses": {
                "willpower": 3
            },
            "starting_jutsu": ["Basic Ninjutsu", "Transformation Jutsu"],
            "color": 10526880  # Gray
        }
    }
    
    # Save clan data
    with open(clans_file, "w", encoding="utf-8") as f:
        json.dump(clans, f, indent=2)
    
    logger.info(f"Created example clan data in {clans_file}")


@bot.event
async def on_ready():
    """Called when the bot is ready."""
    logger.info(f"Logged in as {bot.user.name} ({bot.user.id})")
    
    # Set up dream modules
    try:
        # Set up data directories
        setup_directories()
        
        # Create example clan data
        create_example_clans()
        
        # Set up RPG systems
        systems = setup_rpg_systems(bot, MODULES_CONFIG)
        
        # Sync commands with Discord
        await bot.tree.sync()
        logger.info("Commands synced")
        
        logger.info("Bot setup complete")
    except Exception as e:
        logger.error(f"Error during setup: {e}", exc_info=True)


@bot.event
async def on_message(message):
    """Called when a message is received."""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Process commands
    await bot.process_commands(message)


@bot.command(name="help_rpg")
async def help_rpg(ctx):
    """Display help for RPG commands."""
    embed = discord.Embed(
        title="RPG Commands Help",
        description="Here are the available commands for the RPG system:",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="Character Commands",
        value=(
            "`/create` - Create a new character\n"
            "`/profile` - View your character profile\n"
            "`/delete` - Delete your character (cannot be undone)"
        ),
        inline=False
    )
    
    embed.set_footer(text=f"Type {BOT_CONFIG['command_prefix']}help for regular bot commands")
    
    await ctx.send(embed=embed)


@bot.command(name="shutdown")
@commands.is_owner()
async def shutdown(ctx):
    """Shutdown the bot (owner only)."""
    await ctx.send("Shutting down...")
    
    # Shutdown all systems
    shutdown_all_systems()
    
    # Close the bot
    await bot.close()


def main():
    """Run the bot."""
    # Get the token from environment variable
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("No Discord token found. Set the DISCORD_TOKEN environment variable.")
        return
    
    try:
        # Run the bot
        bot.run(token)
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
    finally:
        # Ensure all systems are shutdown
        shutdown_all_systems()


if __name__ == "__main__":
    main() 