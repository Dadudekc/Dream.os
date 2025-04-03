"""Character management service.

This module provides a character management service that can be used
to create, retrieve, update, and delete characters.
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime
import traceback

from ...core.module_interface import ServiceInterface
from .character_model import Character


class CharacterManager(ServiceInterface):
    """Character management service.
    
    This service provides methods for managing characters, including
    creation, retrieval, updating, and deletion.
    """
    
    def __init__(self, data_dir: str = "data/characters"):
        """Initialize the character manager.
        
        Args:
            data_dir: Directory to store character data
        """
        self._data_dir = data_dir
        self._characters: Dict[str, Character] = {}
        self._logger = logging.getLogger(__name__)
        self._dependencies = {}
        self._config = {
            "data_dir": data_dir,
            "auto_save": True,
            "backup_enabled": True,
            "backup_interval": 3600,  # 1 hour
            "backup_dir": "data/backups/characters",
        }
        
        # Keep track of the last backup time
        self._last_backup = datetime.now()
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the character manager with configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Update configuration
            self._config.update(config)
            
            # Get data directory from config
            self._data_dir = self._config.get("data_dir", self._data_dir)
            
            # Create data directory if it doesn't exist
            os.makedirs(self._data_dir, exist_ok=True)
            
            # Create backup directory if enabled
            if self._config.get("backup_enabled", True):
                backup_dir = self._config.get("backup_dir", "data/backups/characters")
                os.makedirs(backup_dir, exist_ok=True)
            
            # Load characters
            self._load_characters()
            
            self._logger.info(f"CharacterManager initialized with {len(self._characters)} characters")
            return True
        except Exception as e:
            self._logger.error(f"Error initializing CharacterManager: {e}")
            traceback.print_exc()
            return False
    
    def shutdown(self) -> bool:
        """Shutdown the character manager.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        try:
            # Save all characters
            self._save_all_characters()
            
            # Create backup if enabled
            if self._config.get("backup_enabled", True):
                self._create_backup()
            
            self._logger.info("CharacterManager shutdown complete")
            return True
        except Exception as e:
            self._logger.error(f"Error shutting down CharacterManager: {e}")
            return False
    
    @property
    def name(self) -> str:
        """Get the name of the module.
        
        Returns:
            The module name
        """
        return "character_manager"
    
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
        return "Character management service for RPG systems"
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the module.
        
        Returns:
            A dictionary containing status information
        """
        return {
            "loaded_characters": len(self._characters),
            "data_dir": self._data_dir,
            "auto_save": self._config.get("auto_save", True),
            "backup_enabled": self._config.get("backup_enabled", True),
            "last_backup": self._last_backup.isoformat(),
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
            self._logger.warning(f"Dependency '{service_name}' already registered")
            return False
        
        self._dependencies[service_name] = service
        self._logger.debug(f"Registered dependency '{service_name}'")
        return True
    
    def get_service_interface(self) -> Dict[str, Any]:
        """Get the public interface this service provides.
        
        Returns:
            A dictionary of public methods and properties
        """
        return {
            "create_character": self.create_character,
            "get_character": self.get_character,
            "update_character": self.update_character,
            "delete_character": self.delete_character,
            "get_all_characters": self.get_all_characters,
            "save_character": self.save_character,
            "load_character": self.load_character,
        }
    
    def create_character(self, user_id: str, character_data: Dict[str, Any]) -> Optional[Character]:
        """Create a new character.
        
        Args:
            user_id: The ID of the user who owns the character
            character_data: Dictionary of character attributes
            
        Returns:
            The created Character instance, or None if creation failed
        """
        try:
            # Check if the user already has a character
            if user_id in self._characters:
                self._logger.warning(f"User {user_id} already has a character")
                return None
            
            # Create character
            character = Character.from_dict(character_data)
            
            # Store the character
            self._characters[user_id] = character
            
            # Save the character if auto-save is enabled
            if self._config.get("auto_save", True):
                self.save_character(user_id, character)
            
            self._logger.info(f"Created character '{character.name}' for user {user_id}")
            return character
        except Exception as e:
            self._logger.error(f"Error creating character for user {user_id}: {e}")
            traceback.print_exc()
            return None
    
    def get_character(self, user_id: str) -> Optional[Character]:
        """Get a character by user ID.
        
        Args:
            user_id: The ID of the user who owns the character
            
        Returns:
            The Character instance, or None if not found
        """
        # Check if character is already loaded
        if user_id in self._characters:
            return self._characters[user_id]
        
        # Try to load the character from disk
        character = self.load_character(user_id)
        if character:
            # Cache the character
            self._characters[user_id] = character
            return character
        
        return None
    
    def update_character(self, user_id: str, character_data: Dict[str, Any]) -> Optional[Character]:
        """Update an existing character.
        
        Args:
            user_id: The ID of the user who owns the character
            character_data: Dictionary of character attributes to update
            
        Returns:
            The updated Character instance, or None if update failed
        """
        # Get the character
        character = self.get_character(user_id)
        if not character:
            self._logger.warning(f"Cannot update non-existent character for user {user_id}")
            return None
        
        try:
            # Update character attributes
            for key, value in character_data.items():
                if hasattr(character, key):
                    setattr(character, key, value)
            
            # Update timestamp
            character.updated_at = datetime.now().isoformat()
            
            # Save the character if auto-save is enabled
            if self._config.get("auto_save", True):
                self.save_character(user_id, character)
            
            self._logger.info(f"Updated character '{character.name}' for user {user_id}")
            return character
        except Exception as e:
            self._logger.error(f"Error updating character for user {user_id}: {e}")
            return None
    
    def delete_character(self, user_id: str) -> bool:
        """Delete a character.
        
        Args:
            user_id: The ID of the user who owns the character
            
        Returns:
            True if deletion was successful, False otherwise
        """
        # Check if the character exists
        if user_id not in self._characters:
            character_path = os.path.join(self._data_dir, f"{user_id}.json")
            if not os.path.exists(character_path):
                self._logger.warning(f"Cannot delete non-existent character for user {user_id}")
                return False
        
        try:
            # Remove from cache
            if user_id in self._characters:
                character = self._characters[user_id]
                character_name = character.name
                del self._characters[user_id]
            else:
                character_name = "Unknown"
            
            # Remove from disk
            character_path = os.path.join(self._data_dir, f"{user_id}.json")
            if os.path.exists(character_path):
                os.remove(character_path)
            
            self._logger.info(f"Deleted character '{character_name}' for user {user_id}")
            return True
        except Exception as e:
            self._logger.error(f"Error deleting character for user {user_id}: {e}")
            return False
    
    def get_all_characters(self) -> Dict[str, Character]:
        """Get all characters.
        
        Returns:
            Dictionary of user IDs to Character instances
        """
        return self._characters.copy()
    
    def save_character(self, user_id: str, character: Optional[Character] = None) -> bool:
        """Save a character to disk.
        
        Args:
            user_id: The ID of the user who owns the character
            character: The character to save, or None to use the cached character
            
        Returns:
            True if save was successful, False otherwise
        """
        try:
            # Get the character if not provided
            if character is None:
                if user_id not in self._characters:
                    self._logger.warning(f"Cannot save non-existent character for user {user_id}")
                    return False
                character = self._characters[user_id]
            
            # Update timestamp
            character.updated_at = datetime.now().isoformat()
            
            # Create data directory if it doesn't exist
            os.makedirs(self._data_dir, exist_ok=True)
            
            # Save to disk
            character_path = os.path.join(self._data_dir, f"{user_id}.json")
            with open(character_path, "w", encoding="utf-8") as f:
                json.dump(character.to_dict(), f, indent=2)
            
            self._logger.debug(f"Saved character '{character.name}' for user {user_id}")
            
            # Check if we should create a backup
            if self._config.get("backup_enabled", True):
                backup_interval = self._config.get("backup_interval", 3600)
                time_since_backup = (datetime.now() - self._last_backup).total_seconds()
                if time_since_backup >= backup_interval:
                    self._create_backup()
            
            return True
        except Exception as e:
            self._logger.error(f"Error saving character for user {user_id}: {e}")
            traceback.print_exc()
            return False
    
    def load_character(self, user_id: str) -> Optional[Character]:
        """Load a character from disk.
        
        Args:
            user_id: The ID of the user who owns the character
            
        Returns:
            The loaded Character instance, or None if loading failed
        """
        try:
            character_path = os.path.join(self._data_dir, f"{user_id}.json")
            if not os.path.exists(character_path):
                self._logger.debug(f"No character file found for user {user_id}")
                return None
            
            with open(character_path, "r", encoding="utf-8") as f:
                character_data = json.load(f)
            
            character = Character.from_dict(character_data)
            
            self._logger.debug(f"Loaded character '{character.name}' for user {user_id}")
            return character
        except Exception as e:
            self._logger.error(f"Error loading character for user {user_id}: {e}")
            traceback.print_exc()
            return None
    
    def _load_characters(self) -> None:
        """Load all characters from disk."""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self._data_dir, exist_ok=True)
            
            # Load all character files
            for filename in os.listdir(self._data_dir):
                if filename.endswith(".json"):
                    user_id = filename[:-5]  # Remove .json extension
                    character = self.load_character(user_id)
                    if character:
                        self._characters[user_id] = character
            
            self._logger.info(f"Loaded {len(self._characters)} characters from disk")
        except Exception as e:
            self._logger.error(f"Error loading characters: {e}")
            traceback.print_exc()
    
    def _save_all_characters(self) -> None:
        """Save all characters to disk."""
        for user_id, character in self._characters.items():
            self.save_character(user_id, character)
        
        self._logger.info(f"Saved {len(self._characters)} characters to disk")
    
    def _create_backup(self) -> None:
        """Create a backup of all character data."""
        try:
            if not self._config.get("backup_enabled", True):
                return
            
            # Get backup directory
            backup_dir = self._config.get("backup_dir", "data/backups/characters")
            
            # Create backup directory if it doesn't exist
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create backup directory with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, timestamp)
            os.makedirs(backup_path, exist_ok=True)
            
            # Copy all character files to backup directory
            for user_id, character in self._characters.items():
                character_path = os.path.join(backup_path, f"{user_id}.json")
                with open(character_path, "w", encoding="utf-8") as f:
                    json.dump(character.to_dict(), f, indent=2)
            
            # Update last backup time
            self._last_backup = datetime.now()
            
            self._logger.info(f"Created backup of {len(self._characters)} characters at {backup_path}")
        except Exception as e:
            self._logger.error(f"Error creating backup: {e}")
            traceback.print_exc() 