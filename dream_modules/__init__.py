"""Dream modules package.

This package contains modular components that can be used in
various applications, with a focus on Discord bots.
"""

# Export service container
from .core.service_container import ServiceContainer, get_container

# Export base interfaces
from .core.module_interface import (
    ModuleInterface,
    ServiceInterface,
    ConfigurableModule
)

# Export character modules
from .modules.character.character_model import Character
from .modules.character.character_manager import CharacterManager

# Export clan modules
from .modules.clan.clan_model import Clan
from .modules.clan.clan_manager import ClanManager

# Export Discord modules
from .modules.discord.character_commands import CharacterCommands

__version__ = "1.0.0" 