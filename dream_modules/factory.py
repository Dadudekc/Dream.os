"""Factory functions for creating and configuring modules.

This module provides factory functions for creating and configuring
modules, making it easy to integrate them into existing applications.
"""
from typing import Dict, Any, Optional, List
import logging

from .core.service_container import ServiceContainer, get_container
from .core.module_interface import ModuleInterface, ServiceInterface

from .modules.character.character_manager import CharacterManager
from .modules.clan.clan_manager import ClanManager
from .modules.discord.character_commands import CharacterCommands


def create_character_system(config: Optional[Dict[str, Any]] = None) -> CharacterManager:
    """Create a character management system.
    
    Args:
        config: Configuration for the character manager
        
    Returns:
        Configured CharacterManager instance
    """
    container = get_container()
    
    # Create default configuration if not provided
    if config is None:
        config = {}
    
    # Set data directory if not provided
    if "data_dir" not in config:
        config["data_dir"] = "data/characters"
    
    # Create character manager
    character_manager = CharacterManager(config.get("data_dir"))
    
    # Initialize with full configuration
    character_manager.initialize(config)
    
    # Register in container
    container.register("character_manager", character_manager)
    
    return character_manager


def create_clan_system(config: Optional[Dict[str, Any]] = None) -> ClanManager:
    """Create a clan management system.
    
    Args:
        config: Configuration for the clan manager
        
    Returns:
        Configured ClanManager instance
    """
    container = get_container()
    
    # Create default configuration if not provided
    if config is None:
        config = {}
    
    # Set data directory if not provided
    if "data_dir" not in config:
        config["data_dir"] = "data/clans"
    
    # Create clan manager
    clan_manager = ClanManager(config.get("data_dir"))
    
    # Initialize with full configuration
    clan_manager.initialize(config)
    
    # Register in container
    container.register("clan_manager", clan_manager)
    
    return clan_manager


def create_character_commands(bot, config: Optional[Dict[str, Any]] = None) -> CharacterCommands:
    """Create character commands for a Discord bot.
    
    Args:
        bot: Discord bot instance
        config: Configuration for the character commands
        
    Returns:
        Configured CharacterCommands instance
    """
    container = get_container()
    
    # Create default configuration if not provided
    if config is None:
        config = {}
    
    # Check if required services are registered
    if not container.has("character_manager"):
        raise ValueError("Character manager must be created before creating character commands")
    
    if not container.has("clan_manager"):
        raise ValueError("Clan manager must be created before creating character commands")
    
    # Create character commands
    character_commands = CharacterCommands(bot)
    
    # Register dependencies
    character_commands.register_dependency("character_manager", container.get("character_manager"))
    character_commands.register_dependency("clan_manager", container.get("clan_manager"))
    
    # Initialize with full configuration
    character_commands.initialize(config)
    
    # Register in container
    container.register("character_commands", character_commands)
    
    return character_commands


def setup_rpg_systems(bot, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Set up all RPG systems for a Discord bot.
    
    Args:
        bot: Discord bot instance
        config: Configuration for all systems
        
    Returns:
        Dictionary of created systems
    """
    # Create default configuration if not provided
    if config is None:
        config = {}
    
    # Get component configurations
    character_config = config.get("character", {})
    clan_config = config.get("clan", {})
    commands_config = config.get("commands", {})
    
    # Create systems
    character_system = create_character_system(character_config)
    clan_system = create_clan_system(clan_config)
    character_commands = create_character_commands(bot, commands_config)
    
    # Return created systems
    return {
        "character_system": character_system,
        "clan_system": clan_system,
        "character_commands": character_commands
    }


def shutdown_all_systems() -> bool:
    """Shutdown all registered systems.
    
    Returns:
        True if all systems were shutdown successfully, False otherwise
    """
    container = get_container()
    logger = logging.getLogger(__name__)
    
    success = True
    
    # Get all registered services
    services = container._services
    
    # Shutdown each service that implements ModuleInterface
    for name, service in services.items():
        if isinstance(service, ModuleInterface):
            try:
                service.shutdown()
                logger.info(f"Shut down {name}")
            except Exception as e:
                logger.error(f"Error shutting down {name}: {e}")
                success = False
    
    return success 