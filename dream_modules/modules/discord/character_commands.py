"""Discord character commands module.

This module provides Discord commands for character management,
using the character and clan services.
"""
import discord
from discord.ext import commands
from discord import ui, app_commands
from typing import Dict, Any, Optional, List, Union
import logging
import asyncio
import traceback
from datetime import datetime

from ...core.module_interface import ServiceInterface
from ..character.character_model import Character


class DeleteConfirmationView(ui.View):
    """View for confirming character deletion."""
    
    def __init__(self, character_commands, user, character, timeout=60):
        """Initialize the delete confirmation view.
        
        Args:
            character_commands: The character commands instance
            user: The Discord user
            character: The character to delete
            timeout: View timeout in seconds
        """
        super().__init__(timeout=timeout)
        self.character_commands = character_commands
        self.user = user
        self.character = character
        
    @ui.button(label="Yes, Delete My Character", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, interaction: discord.Interaction, button: ui.Button):
        """Confirm character deletion."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This is not your character to delete!", ephemeral=True)
            return
            
        # Process the deletion
        success, message = await self.character_commands._delete_character(self.user, self.character)
        
        # Disable all buttons
        for child in self.children:
            child.disabled = True
            
        await interaction.response.edit_message(content=message, view=self)
        self.stop()
        
    @ui.button(label="No, Keep My Character", style=discord.ButtonStyle.success)
    async def cancel_delete(self, interaction: discord.Interaction, button: ui.Button):
        """Cancel character deletion."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This is not your character to delete!", ephemeral=True)
            return
            
        # Disable all buttons
        for child in self.children:
            child.disabled = True
            
        await interaction.response.edit_message(content="✅ Character deletion cancelled.", view=self)
        self.stop()
        
    async def on_timeout(self):
        """Handle timeout."""
        # Disable all buttons on timeout
        for child in self.children:
            child.disabled = True
        
        try:
            # Try to edit the message if it still exists
            await self.message.edit(content="⏰ Character deletion request timed out.", view=self)
        except:
            pass


class CharacterNameModal(ui.Modal, title='Create Your Character'):
    """Modal for entering character name during creation."""
    
    name_input = ui.TextInput(
        label='Character Name',
        placeholder='Enter your desired character name (3-20 characters)',
        min_length=3,
        max_length=20,
        required=True
    )

    def __init__(self, character_commands):
        """Initialize the character name modal.
        
        Args:
            character_commands: The character commands instance
        """
        super().__init__()
        self.character_commands = character_commands

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        name = self.name_input.value.strip()
        await self.character_commands._process_character_creation(interaction, name)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Handle modal errors."""
        logging.error(f'Error in CharacterNameModal: {error}', exc_info=True)
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)


class CharacterCommands(ServiceInterface):
    """Discord commands for character management.
    
    This service provides Discord commands for managing characters,
    integrating with the character and clan services.
    """
    
    def __init__(self, bot):
        """Initialize the character commands.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self._dependencies = {}
        self._config = {
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
        self.command_cooldowns = {}
        self.role_cache = {}
        
        # Store references to the required services
        self.character_system = None
        self.clan_data = None
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the character commands with configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Update configuration
            self._config.update(config)
            
            # Check if required services are registered
            if "character_manager" not in self._dependencies:
                self.logger.error("Character manager service not registered")
                return False
            
            if "clan_manager" not in self._dependencies:
                self.logger.error("Clan manager service not registered")
                return False
            
            # Get service references
            self.character_system = self._dependencies["character_manager"]
            self.clan_data = self._dependencies["clan_manager"]
            
            # Register commands
            self.register_commands(self.bot.tree)
            
            self.logger.info("CharacterCommands initialized")
            return True
        except Exception as e:
            self.logger.error(f"Error initializing CharacterCommands: {e}")
            traceback.print_exc()
            return False
    
    def shutdown(self) -> bool:
        """Shutdown the character commands.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        try:
            self.logger.info("CharacterCommands shutdown complete")
            return True
        except Exception as e:
            self.logger.error(f"Error shutting down CharacterCommands: {e}")
            return False
    
    @property
    def name(self) -> str:
        """Get the name of the module.
        
        Returns:
            The module name
        """
        return "character_commands"
    
    @property
    def version(self) -> str:
        """Get the version of the module.
        
        Returns:
            The module version
        """
        return "1.0.0"
    
    @property
    def description(self) -> str:
        """Get a description of the module.
        
        Returns:
            The module description
        """
        return "Discord commands for character management"
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the module.
        
        Returns:
            A dictionary containing status information
        """
        return {
            "active_cooldowns": len(self.command_cooldowns),
            "role_cache_size": len(self.role_cache),
            "role_management_enabled": self._config.get("role_management", {}).get("enabled", True)
        }
    
    def register_dependency(self, service_name: str, service: Any) -> bool:
        """Register a dependency for this service.
        
        Args:
            service_name: The name of the service
            service: The service instance
            
        Returns:
            True if registration was successful, False otherwise
        """
        if service_name in self._dependencies:
            self.logger.warning(f"Dependency '{service_name}' already registered")
            return False
        
        self._dependencies[service_name] = service
        self.logger.debug(f"Registered dependency '{service_name}'")
        return True
    
    def get_service_interface(self) -> Dict[str, Any]:
        """Get the public interface this service provides.
        
        Returns:
            A dictionary of public methods and properties
        """
        return {
            "register_commands": self.register_commands
        }
    
    def register_commands(self, tree: app_commands.CommandTree) -> None:
        """Register character-related commands to the app command tree.
        
        Args:
            tree: The application command tree to register commands to
        """
        self.logger.info("Registering character commands: create, profile, delete")
        
        # Check if commands already exist to avoid re-registration
        existing_commands = [cmd.name for cmd in tree.get_commands()]
        
        if "create" not in existing_commands:
            @tree.command(name="create", description="Create your character")
            async def create_character(interaction: discord.Interaction):
                """Create a new character."""
                await interaction.response.send_modal(CharacterNameModal(self))
        
        if "profile" not in existing_commands:
            @tree.command(name="profile", description="View your or another user's character profile")
            @app_commands.describe(user="The user whose profile to view. If not provided, views your own profile.")
            async def profile(interaction: discord.Interaction, user: Optional[discord.User] = None):
                """View a character profile."""
                # If no user is specified, use the command invoker
                target_user = user or interaction.user
                
                # Check if the user has a character
                character = self.character_system.get_character(str(target_user.id))
                if not character:
                    if target_user.id == interaction.user.id:
                        await interaction.response.send_message("You don't have a character yet! Use `/create` to make one.")
                    else:
                        await interaction.response.send_message(f"{target_user.display_name} doesn't have a character yet!")
                    return
                
                # Create and send the embed
                embed = self._create_character_embed(character, target_user)
                await interaction.response.send_message(embed=embed)
        
        if "delete" not in existing_commands:
            @tree.command(name="delete", description="Delete your character (cannot be undone)")
            async def delete_character(interaction: discord.Interaction):
                """Delete your character."""
                await self.delete_character_slash(interaction)
    
    def _create_character_embed(self, character: Character, user: discord.User) -> discord.Embed:
        """Create a Discord embed to display character information.
        
        Args:
            character: The character object
            user: The Discord user object
            
        Returns:
            A Discord embed containing the character information
        """
        # Get clan info for color
        clan_info = self.clan_data.get_clan(character.clan)
        clan_rarity_str = "Unknown"
        rarity_color = discord.Color.default()
        if clan_info:
            clan_rarity_str = clan_info.rarity
            # Convert string color to Discord color
            try:
                rarity_color = discord.Color(clan_info.color)
            except:
                # Default colors based on rarity
                color_map = {
                    "Common": discord.Color.light_grey(),
                    "Uncommon": discord.Color.green(),
                    "Rare": discord.Color.blue(),
                    "Epic": discord.Color.purple(),
                    "Legendary": discord.Color.gold()
                }
                rarity_color = color_map.get(clan_rarity_str, discord.Color.default())
        
        # Create embed
        embed = discord.Embed(
            title=f"{character.name}'s Profile",
            description=f"Clan: {character.clan} ({clan_rarity_str})",
            color=rarity_color
        )
        
        # Add character info
        embed.add_field(name="Clan", value=character.clan if hasattr(character, 'clan') and character.clan else "None", inline=True)
        embed.add_field(name="Rank", value=character.rank if hasattr(character, 'rank') else "Academy Student", inline=True)
        embed.add_field(name="Specialization", value=character.specialization if hasattr(character, 'specialization') else "None", inline=True)
        
        # Add stats - handle both dictionary stats or individual attributes
        stats_text = ""
        if hasattr(character, 'stats') and isinstance(character.stats, dict):
            # If stats is a dictionary attribute
            for stat_name, stat_value in character.stats.items():
                stats_text += f"{stat_name.replace('_', ' ').title()}: **{stat_value}**\n"
        else:
            # Try to access individual stat attributes
            stat_attributes = [
                'ninjutsu', 'taijutsu', 'genjutsu', 'intelligence', 
                'strength', 'speed', 'stamina', 'chakra_control', 
                'perception', 'willpower'
            ]
            for stat_name in stat_attributes:
                if hasattr(character, stat_name):
                    stat_value = getattr(character, stat_name)
                    stats_text += f"{stat_name.replace('_', ' ').title()}: **{stat_value}**\n"
        
        embed.add_field(name="Stats", value=stats_text or "No stats available", inline=False)
        
        # Add inventory summary
        inventory_count = len(character.inventory) if hasattr(character, 'inventory') else 0
        embed.add_field(name="Inventory", value=f"{inventory_count} items", inline=True)
        
        # Add jutsu summary
        jutsu_count = len(character.jutsu) if hasattr(character, 'jutsu') else 0
        embed.add_field(name="Jutsu", value=f"Known: {jutsu_count}", inline=True)
        
        # Add experience
        embed.add_field(
            name="Experience",
            value=f"{character.exp}/{character.level * 100} XP",
            inline=True
        )
        
        # Set footer with character ID
        embed.set_footer(text=f"Character ID: {user.id}")
        
        # Set user avatar if available
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
            
        return embed
    
    async def _process_character_creation(self, interaction: discord.Interaction, name: str):
        """Process character creation after name is provided.
        
        Args:
            interaction: The Discord interaction
            name: The character name
        """
        # Validate name
        if len(name) < 3 or len(name) > 20:
            await interaction.response.send_message(
                "❌ Character name must be between 3 and 20 characters.",
                ephemeral=True
            )
            return
        
        # Create embed for options
        embed = discord.Embed(
            title="Create Your Character",
            description=f"Creating a new character named **{name}**",
            color=discord.Color.blue()
        )
        
        # Create view with buttons
        class CreateOptionsView(ui.View):
            def __init__(self, cog, char_name):
                super().__init__(timeout=180)
                self.cog = cog
                self.char_name = char_name
                
            @ui.button(label="Create Character", style=discord.ButtonStyle.primary)
            async def create_character(self, interaction: discord.Interaction, button: ui.Button):
                await self.cog._create_character_logic(interaction, self.char_name)
                self.stop()
                
            @ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, interaction: discord.Interaction, button: ui.Button):
                await interaction.response.send_message("Character creation cancelled.", ephemeral=True)
                self.stop()
        
        # Send options to user
        await interaction.response.send_message(embed=embed, view=CreateOptionsView(self, name), ephemeral=True)
    
    async def _create_character_logic(self, interaction: discord.Interaction, name: str):
        """Core logic for creating a character.
        
        Args:
            interaction: The Discord interaction
            name: The character name
        """
        try:
            user_id = str(interaction.user.id)
            
            # Check if user already has a character
            existing_character = self.character_system.get_character(user_id)
            if existing_character:
                await interaction.response.send_message(
                    f"❌ You already have a character named **{existing_character.name}**! Use `/delete` if you want to start over.",
                    ephemeral=True
                )
                return
            
            # Create character data
            character_data = {
                "name": name,
                "clan": "Civilian",  # Default clan
                "level": 1,
                "exp": 0,
                "ninjutsu": 10,
                "taijutsu": 10,
                "genjutsu": 10,
                "intelligence": 10,
                "strength": 10,
                "speed": 10,
                "stamina": 10,
                "chakra_control": 10,
                "perception": 10,
                "willpower": 10
            }
            
            # Create character
            character = self.character_system.create_character(user_id, character_data)
            if not character:
                await interaction.response.send_message(
                    "❌ Failed to create character. Please try again later.",
                    ephemeral=True
                )
                return
            
            # Create response embed
            embed = discord.Embed(
                title="✅ Character Created!",
                description=f"Welcome, **{name}**! Your journey begins now.",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Next Steps",
                value=(
                    "• Use `/profile` to view your stats\n"
                    "• Use `/train` to improve your abilities\n"
                    "• Use `/help` to see all available commands"
                ),
                inline=False
            )
            
            # Send response
            response_method = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
            await response_method(embed=embed)
            
            # Update roles
            if interaction.guild and self._config.get("role_management", {}).get("enabled", True):
                try:
                    await self._update_roles_from_interaction(interaction, character)
                except Exception as e:
                    self.logger.error(f"Error updating roles after creation for {user_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error in _create_character_logic for {interaction.user.id}: {e}", exc_info=True)
            # Try to respond with an error message
            try:
                response_method = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
                await response_method(
                    "❌ An unexpected error occurred during character creation. Please try again later.",
                    ephemeral=True
                )
            except:
                pass
    
    async def delete_character_slash(self, interaction: discord.Interaction):
        """Delete a character using slash command.
        
        Args:
            interaction: The interaction object
        """
        user_id = str(interaction.user.id)
        character = self.character_system.get_character(user_id)
        
        if not character:
            await interaction.response.send_message("❌ You don't have a character to delete!", ephemeral=True)
            return
        
        # Create confirmation message
        confirm_view = DeleteConfirmationView(self, interaction.user, character)
        await interaction.response.send_message(
            f"⚠️ **WARNING:** Are you sure you want to delete your character **{character.name}**?\n"
            "This action cannot be undone!",
            view=confirm_view,
            ephemeral=True
        )
    
    async def _delete_character(self, user, character):
        """Actually delete a character after confirmation.
        
        Args:
            user: The Discord user
            character: The character to delete
            
        Returns:
            Tuple of (success, message)
        """
        user_id = str(user.id)
        try:
            # Delete the character
            success = self.character_system.delete_character(user_id)
            
            if success:
                self.logger.info(f"Character {character.name} deleted for user {user_id}")
                return True, f"✅ Character **{character.name}** has been permanently deleted."
            else:
                self.logger.error(f"Failed to delete character for user {user_id}")
                return False, "❌ Failed to delete character. Please try again later."
        except Exception as e:
            self.logger.error(f"Error deleting character for user {user_id}: {e}", exc_info=True)
            return False, "❌ An error occurred while deleting your character. Please try again later."
    
    async def _update_roles_from_interaction(self, interaction: discord.Interaction, character: Character) -> None:
        """Update roles for a user based on interaction.
        
        Args:
            interaction: The Discord interaction
            character: The character object
        """
        # Ensure we have guild and member objects. For interactions, user is the member.
        member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        guild = interaction.guild
        
        if not guild or not member:
            self.logger.warning(f"Could not update roles for user {interaction.user.id}: Missing guild or member object.")
            return
        
        try:
            role_config = self._config.get("role_management", {})
            
            # Handle level roles
            await self._handle_level_roles(guild, member, character)
            
            # Handle clan roles
            if role_config.get("clan_roles", True):
                await self._handle_clan_roles(guild, member, character)
            
            # Handle specialization roles
            if hasattr(character, 'specialization') and character.specialization:
                await self._handle_specialization_roles(guild, member, character)
            
            self.logger.info(f"Updated roles for {member.display_name} (ID: {member.id}) in guild {guild.name}")
        except discord.errors.Forbidden:
            self.logger.error(f"Permission error updating roles for {member.display_name} in guild {guild.name}. Check bot permissions.")
        except Exception as e:
            self.logger.error(f"Error updating roles for {member.display_name}: {e}", exc_info=True)
    
    async def _handle_level_roles(self, guild, member, character: Character) -> None:
        """Handle level-based role assignments.
        
        Args:
            guild: The Discord guild
            member: The Discord member
            character: The character object
        """
        # Get role configuration
        role_config = self._config.get("role_management", {})
        level_roles = role_config.get("level_roles", {})
        
        # Get all level roles
        role_map = {}
        for level, role_name in level_roles.items():
            role = await self._get_or_create_role(guild, role_name)
            if role:
                role_map[level] = role
        
        # Sort levels in descending order
        sorted_levels = sorted(role_map.keys(), reverse=True)
        
        # Find the highest level role the character qualifies for
        qualified_role = None
        for level in sorted_levels:
            if character.level >= level:
                qualified_role = role_map[level]
                break
        
        if not qualified_role:
            return
        
        # Remove all level roles
        for role in role_map.values():
            if role in member.roles and role != qualified_role:
                await member.remove_roles(role, reason="Character level role update")
        
        # Add the qualified role if not already assigned
        if qualified_role not in member.roles:
            await member.add_roles(qualified_role, reason="Character level role update")
    
    async def _handle_clan_roles(self, guild, member, character: Character) -> None:
        """Handle clan-based role assignments.
        
        Args:
            guild: The Discord guild
            member: The Discord member
            character: The character object
        """
        # Get clans from the clan manager
        clans = [clan_obj.name for clan_obj in self.clan_data.get_all_clans().values()]
        
        # Create a list to store clan roles
        clan_roles = []
        
        # Get or create the role for each clan
        for clan_name in clans:
            role = await self._get_or_create_role(guild, clan_name)
            if role:
                clan_roles.append(role)
        
        # Get the role corresponding to the character's clan
        character_clan_role = next((r for r in clan_roles if r.name.lower() == character.clan.lower()), None)
        
        # Remove all clan roles except the character's clan
        for role in clan_roles:
            if role in member.roles and role != character_clan_role:
                await member.remove_roles(role, reason="Character clan role update")
        
        # Add the character's clan role if not already assigned
        if character_clan_role and character_clan_role not in member.roles:
            await member.add_roles(character_clan_role, reason="Character clan role update")
    
    async def _handle_specialization_roles(self, guild, member, character: Character) -> None:
        """Handle specialization-based role assignments.
        
        Args:
            guild: The Discord guild
            member: The Discord member
            character: The character object
        """
        # Get role configuration
        role_config = self._config.get("role_management", {})
        specialization_roles = role_config.get("specialization_roles", {})
        
        # Create roles map
        spec_role_map = {}
        for spec, role_name in specialization_roles.items():
            role = await self._get_or_create_role(guild, role_name)
            if role:
                spec_role_map[spec] = role
        
        # Get the character's specialization
        character_spec = character.specialization
        character_spec_role = spec_role_map.get(character_spec, None)
        
        # Remove all specialization roles except the character's specialization
        for role in spec_role_map.values():
            if role in member.roles and role != character_spec_role:
                await member.remove_roles(role, reason="Character specialization role update")
        
        # Add the character's specialization role if not already assigned
        if character_spec_role and character_spec_role not in member.roles:
            await member.add_roles(character_spec_role, reason="Character specialization role update")
    
    async def _get_or_create_role(self, guild, role_name: str) -> Optional[discord.Role]:
        """Get or create a role in the guild.
        
        Args:
            guild: The Discord guild
            role_name: The name of the role
            
        Returns:
            The role object or None if failed
        """
        # Check if the role is already cached
        cache_key = f"{guild.id}:{role_name}"
        if cache_key in self.role_cache:
            role = guild.get_role(self.role_cache[cache_key])
            if role:
                return role
        
        # Try to get the role
        role = discord.utils.get(guild.roles, name=role_name)
        
        # Create the role if it doesn't exist
        if not role:
            try:
                self.logger.info(f"Creating role '{role_name}' in guild {guild.name}")
                role = await guild.create_role(
                    name=role_name,
                    reason="Automatic role creation for character progression"
                )
            except Exception as e:
                self.logger.error(f"Failed to create role '{role_name}': {e}", exc_info=True)
                return None
        
        # Cache the role ID
        if role:
            self.role_cache[cache_key] = role.id
        
        return role 