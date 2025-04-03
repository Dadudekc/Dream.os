"""Clan management service.

This module provides a clan management service that can be used
to retrieve and manage clan data.
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
import traceback

from ...core.module_interface import ServiceInterface
from .clan_model import Clan


class ClanManager(ServiceInterface):
    """Clan management service.
    
    This service provides methods for managing clan data,
    including retrieval and updating of clan information.
    """
    
    def __init__(self, data_dir: str = "data/clans"):
        """Initialize the clan manager.
        
        Args:
            data_dir: Directory to store clan data
        """
        self._data_dir = data_dir
        self._clans: Dict[str, Clan] = {}
        self._logger = logging.getLogger(__name__)
        self._dependencies = {}
        self._config = {
            "data_dir": data_dir,
            "auto_save": True,
            "clans_file": "clans.json",
        }
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the clan manager with configuration.
        
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
            
            # Load clans
            self._load_clans()
            
            self._logger.info(f"ClanManager initialized with {len(self._clans)} clans")
            return True
        except Exception as e:
            self._logger.error(f"Error initializing ClanManager: {e}")
            traceback.print_exc()
            return False
    
    def shutdown(self) -> bool:
        """Shutdown the clan manager.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        try:
            # Save all clans
            self._save_all_clans()
            
            self._logger.info("ClanManager shutdown complete")
            return True
        except Exception as e:
            self._logger.error(f"Error shutting down ClanManager: {e}")
            return False
    
    @property
    def name(self) -> str:
        """Get the name of the module.
        
        Returns:
            The module name
        """
        return "clan_manager"
    
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
        return "Clan management service for RPG systems"
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the module.
        
        Returns:
            A dictionary containing status information
        """
        return {
            "loaded_clans": len(self._clans),
            "data_dir": self._data_dir,
            "auto_save": self._config.get("auto_save", True),
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
            "get_clan": self.get_clan,
            "get_all_clans": self.get_all_clans,
            "get_clans_by_rarity": self.get_clans_by_rarity,
            "get_clan_bonuses": self.get_clan_bonuses,
            "get_clan_jutsu": self.get_clan_jutsu,
        }
    
    def get_clan(self, clan_name: str) -> Optional[Clan]:
        """Get a clan by name.
        
        Args:
            clan_name: The name of the clan
            
        Returns:
            The Clan instance, or None if not found
        """
        return self._clans.get(clan_name.lower())
    
    def get_all_clans(self) -> Dict[str, Clan]:
        """Get all clans.
        
        Returns:
            Dictionary of clan names to Clan instances
        """
        return self._clans.copy()
    
    def get_clans_by_rarity(self, rarity: str) -> List[Clan]:
        """Get all clans of a specific rarity.
        
        Args:
            rarity: The rarity to filter by
            
        Returns:
            List of Clan instances with the specified rarity
        """
        return [clan for clan in self._clans.values() if clan.rarity.lower() == rarity.lower()]
    
    def get_clan_bonuses(self, clan_name: str) -> Dict[str, int]:
        """Get the stat bonuses for a clan.
        
        Args:
            clan_name: The name of the clan
            
        Returns:
            Dictionary of stat names to bonus values, or empty dict if clan not found
        """
        clan = self.get_clan(clan_name)
        if not clan:
            return {}
        
        return clan.stat_bonuses.copy()
    
    def get_clan_jutsu(self, clan_name: str) -> List[str]:
        """Get the starting jutsu for a clan.
        
        Args:
            clan_name: The name of the clan
            
        Returns:
            List of jutsu names, or empty list if clan not found
        """
        clan = self.get_clan(clan_name)
        if not clan:
            return []
        
        return clan.starting_jutsu.copy()
    
    def create_clan(self, clan_data: Dict[str, Any]) -> Optional[Clan]:
        """Create a new clan.
        
        Args:
            clan_data: Dictionary of clan attributes
            
        Returns:
            The created Clan instance, or None if creation failed
        """
        try:
            # Check if clan name is provided
            if "name" not in clan_data:
                self._logger.warning("Cannot create clan without a name")
                return None
            
            # Check if the clan already exists
            clan_name = clan_data["name"]
            if clan_name.lower() in self._clans:
                self._logger.warning(f"Clan '{clan_name}' already exists")
                return None
            
            # Create clan
            clan = Clan.from_dict(clan_data)
            
            # Store the clan
            self._clans[clan_name.lower()] = clan
            
            # Save the clan if auto-save is enabled
            if self._config.get("auto_save", True):
                self._save_all_clans()
            
            self._logger.info(f"Created clan '{clan_name}'")
            return clan
        except Exception as e:
            self._logger.error(f"Error creating clan: {e}")
            traceback.print_exc()
            return None
    
    def update_clan(self, clan_name: str, clan_data: Dict[str, Any]) -> Optional[Clan]:
        """Update an existing clan.
        
        Args:
            clan_name: The name of the clan to update
            clan_data: Dictionary of clan attributes to update
            
        Returns:
            The updated Clan instance, or None if update failed
        """
        try:
            # Check if the clan exists
            clan = self.get_clan(clan_name)
            if not clan:
                self._logger.warning(f"Cannot update non-existent clan '{clan_name}'")
                return None
            
            # Update clan attributes
            for key, value in clan_data.items():
                if hasattr(clan, key):
                    setattr(clan, key, value)
            
            # Save the clan if auto-save is enabled
            if self._config.get("auto_save", True):
                self._save_all_clans()
            
            self._logger.info(f"Updated clan '{clan_name}'")
            return clan
        except Exception as e:
            self._logger.error(f"Error updating clan '{clan_name}': {e}")
            return None
    
    def delete_clan(self, clan_name: str) -> bool:
        """Delete a clan.
        
        Args:
            clan_name: The name of the clan to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Check if the clan exists
            if clan_name.lower() not in self._clans:
                self._logger.warning(f"Cannot delete non-existent clan '{clan_name}'")
                return False
            
            # Remove from cache
            del self._clans[clan_name.lower()]
            
            # Save the changes if auto-save is enabled
            if self._config.get("auto_save", True):
                self._save_all_clans()
            
            self._logger.info(f"Deleted clan '{clan_name}'")
            return True
        except Exception as e:
            self._logger.error(f"Error deleting clan '{clan_name}': {e}")
            return False
    
    def _load_clans(self) -> None:
        """Load clans from disk."""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self._data_dir, exist_ok=True)
            
            # Get clans file path
            clans_file = self._config.get("clans_file", "clans.json")
            clans_path = os.path.join(self._data_dir, clans_file)
            
            # Check if the file exists
            if not os.path.exists(clans_path):
                self._logger.warning(f"Clans file not found at {clans_path}")
                return
            
            # Load clans from file
            with open(clans_path, "r", encoding="utf-8") as f:
                clans_data = json.load(f)
            
            # Check if it's a list or dictionary
            if isinstance(clans_data, list):
                # List of clan dictionaries
                for clan_data in clans_data:
                    if "name" in clan_data:
                        clan = Clan.from_dict(clan_data)
                        self._clans[clan.name.lower()] = clan
            elif isinstance(clans_data, dict):
                # Dictionary of clan name to clan data
                for clan_name, clan_data in clans_data.items():
                    if isinstance(clan_data, dict):
                        # Ensure name is in the data
                        if "name" not in clan_data:
                            clan_data["name"] = clan_name
                        
                        clan = Clan.from_dict(clan_data)
                        self._clans[clan.name.lower()] = clan
            
            self._logger.info(f"Loaded {len(self._clans)} clans from {clans_path}")
        except Exception as e:
            self._logger.error(f"Error loading clans: {e}")
            traceback.print_exc()
    
    def _save_all_clans(self) -> None:
        """Save all clans to disk."""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self._data_dir, exist_ok=True)
            
            # Get clans file path
            clans_file = self._config.get("clans_file", "clans.json")
            clans_path = os.path.join(self._data_dir, clans_file)
            
            # Convert clans to dictionary
            clans_data = {clan.name: clan.to_dict() for clan in self._clans.values()}
            
            # Save to disk
            with open(clans_path, "w", encoding="utf-8") as f:
                json.dump(clans_data, f, indent=2)
            
            self._logger.info(f"Saved {len(self._clans)} clans to {clans_path}")
        except Exception as e:
            self._logger.error(f"Error saving clans: {e}")
            traceback.print_exc() 