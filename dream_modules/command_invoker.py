"""Command invoker script for testing Discord slash commands.

This script simulates Discord interactions to test slash commands
in a controlled environment without needing a Discord connection.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

# Import bot and command modules
from HCshinobi.bot import bot
from HCshinobi.commands.character_commands import CharacterCommands
from HCshinobi.commands.clan_commands import ClanCommands
from HCshinobi.commands.mission_commands import MissionCommands
from HCshinobi.commands.npc_commands import NPCCommands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MockUser:
    """Mock Discord user for testing."""
    id: int = 123456789
    name: str = "TestUser"
    display_name: str = "Test User"
    bot: bool = False
    
    def __str__(self) -> str:
        return self.name


@dataclass
class MockGuild:
    """Mock Discord guild for testing."""
    id: int = 987654321
    name: str = "Test Guild"


class MockInteraction:
    """Mock Discord interaction for testing slash commands."""
    
    def __init__(
        self,
        command_name: str,
        options: Dict[str, Any] = None,
        user: Optional[MockUser] = None,
        guild: Optional[MockGuild] = None
    ):
        self.command_name = command_name
        self.options = options or {}
        self.user = user or MockUser()
        self.guild = guild or MockGuild()
        self.response_sent = False
        self.deferred = False
        self.responses: List[Dict[str, Any]] = []
    
    async def response_mock(self, *args, **kwargs):
        """Mock interaction response."""
        self.response_sent = True
        self.responses.append({
            "args": args,
            "kwargs": kwargs,
            "timestamp": datetime.now()
        })
        return None
    
    async def defer(self, *args, **kwargs):
        """Mock defer response."""
        self.deferred = True
        return None
    
    def get_option(self, name: str) -> Any:
        """Get option value by name."""
        return self.options.get(name)
    
    @property
    def response(self):
        """Mock response property."""
        return type("MockResponse", (), {
            "send_message": self.response_mock,
            "send_modal": self.response_mock,
            "defer": self.defer
        })()


class CommandInvoker:
    """Test invoker for Discord slash commands."""
    
    def __init__(self):
        """Initialize the command invoker."""
        self.bot = bot
        self.character_commands = CharacterCommands(self.bot)
        self.clan_commands = ClanCommands(self.bot)
        self.mission_commands = MissionCommands(self.bot)
        self.npc_commands = NPCCommands(self.bot)
    
    async def invoke_command(
        self,
        command_name: str,
        options: Dict[str, Any] = None,
        user: Optional[MockUser] = None,
        guild: Optional[MockGuild] = None
    ) -> MockInteraction:
        """Invoke a slash command with mock interaction.
        
        Args:
            command_name: Name of the command to invoke
            options: Command options/parameters
            user: Mock user to use (optional)
            guild: Mock guild to use (optional)
            
        Returns:
            MockInteraction with response data
        """
        interaction = MockInteraction(command_name, options, user, guild)
        
        try:
            # Map command to appropriate handler
            command_map = {
                # Character commands
                "create": self.character_commands.create_character_cmd,
                "profile": self.character_commands.profile_cmd,
                "delete": self.character_commands.delete_character_cmd,
                
                # Clan commands
                "clan list": self.clan_commands.list_clans_cmd,
                "clan info": self.clan_commands.clan_info_cmd,
                
                # Mission commands
                "mission assign": self.mission_commands.assign_mission_cmd,
                "mission complete": self.mission_commands.complete_mission_cmd,
                
                # NPC commands
                "npc mark_death": self.npc_commands.mark_npc_death_cmd,
                "npc list": self.npc_commands.list_npcs_cmd,
            }
            
            if command_name not in command_map:
                raise ValueError(f"Unknown command: {command_name}")
            
            # Invoke the command
            await command_map[command_name](interaction)
            
            logger.info(
                f"Command '{command_name}' invoked successfully with "
                f"{len(interaction.responses)} response(s)"
            )
            
        except Exception as e:
            logger.error(f"Error invoking command '{command_name}': {e}")
            raise
        
        return interaction
    
    async def test_character_commands(self):
        """Test character-related commands."""
        logger.info("Testing character commands...")
        
        # Test character creation
        create_interaction = await self.invoke_command(
            "create",
            options={"name": "TestCharacter", "clan": "Uchiha"}
        )
        assert create_interaction.response_sent
        
        # Test character profile
        profile_interaction = await self.invoke_command(
            "profile",
            options={"user": MockUser()}
        )
        assert profile_interaction.response_sent
        
        # Test character deletion
        delete_interaction = await self.invoke_command(
            "delete",
            options={"confirm": True}
        )
        assert delete_interaction.response_sent
        
        logger.info("Character command tests completed")
    
    async def test_clan_commands(self):
        """Test clan-related commands."""
        logger.info("Testing clan commands...")
        
        # Test clan list
        list_interaction = await self.invoke_command("clan list")
        assert list_interaction.response_sent
        
        # Test clan info
        info_interaction = await self.invoke_command(
            "clan info",
            options={"clan_name": "Uchiha"}
        )
        assert info_interaction.response_sent
        
        logger.info("Clan command tests completed")
    
    async def test_mission_commands(self):
        """Test mission-related commands."""
        logger.info("Testing mission commands...")
        
        # Test mission assignment
        assign_interaction = await self.invoke_command(
            "mission assign",
            options={"difficulty": "easy"}
        )
        assert assign_interaction.response_sent
        
        # Test mission completion
        complete_interaction = await self.invoke_command(
            "mission complete",
            options={"mission_id": "test_mission"}
        )
        assert complete_interaction.response_sent
        
        logger.info("Mission command tests completed")
    
    async def test_npc_commands(self):
        """Test NPC-related commands."""
        logger.info("Testing NPC commands...")
        
        # Test NPC death marking
        death_interaction = await self.invoke_command(
            "npc mark_death",
            options={"npc_name": "TestNPC", "cause": "Testing"}
        )
        assert death_interaction.response_sent
        
        # Test NPC listing
        list_interaction = await self.invoke_command("npc list")
        assert list_interaction.response_sent
        
        logger.info("NPC command tests completed")
    
    async def run_all_tests(self):
        """Run all command tests."""
        logger.info("Starting command tests...")
        
        try:
            await self.test_character_commands()
            await self.test_clan_commands()
            await self.test_mission_commands()
            await self.test_npc_commands()
            
            logger.info("All command tests completed successfully!")
            
        except Exception as e:
            logger.error(f"Command tests failed: {e}")
            raise


async def main():
    """Run the command invoker tests."""
    invoker = CommandInvoker()
    await invoker.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main()) 