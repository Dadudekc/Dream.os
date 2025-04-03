"""Clan model for the RPG system.

This module provides a standalone Clan class that can be used
in any RPG system that requires clan management.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
import json


@dataclass
class Clan:
    """Clan model for the RPG system."""
    
    # Basic information
    name: str
    rarity: str = "Common"
    
    # Clan details
    lore: str = ""
    description: str = ""
    special_ability: str = ""
    
    # Bonuses and properties
    stat_bonuses: Dict[str, int] = field(default_factory=dict)
    starting_jutsu: List[str] = field(default_factory=list)
    special_techniques: List[str] = field(default_factory=list)
    available_kekkei_genkai: List[str] = field(default_factory=list)
    
    # Visual elements
    emblem_url: str = ""
    color: int = 0  # Discord color integer
    
    # Additional properties
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert clan to a dictionary.
        
        Returns:
            Dictionary representation of the clan
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Clan':
        """Create a clan from a dictionary.
        
        Args:
            data: Dictionary data to create clan from
            
        Returns:
            A new Clan instance
        """
        # Handle nested structures
        stat_bonuses = data.get('stat_bonuses', {})
        if not isinstance(stat_bonuses, dict):
            stat_bonuses = {}
        
        starting_jutsu = data.get('starting_jutsu', [])
        if not isinstance(starting_jutsu, list):
            starting_jutsu = []
        
        special_techniques = data.get('special_techniques', [])
        if not isinstance(special_techniques, list):
            special_techniques = []
        
        available_kekkei_genkai = data.get('available_kekkei_genkai', [])
        if not isinstance(available_kekkei_genkai, list):
            available_kekkei_genkai = []
        
        properties = data.get('properties', {})
        if not isinstance(properties, dict):
            properties = {}
        
        # Create the clan instance
        return cls(
            name=data.get('name', ''),
            rarity=data.get('rarity', 'Common'),
            lore=data.get('lore', ''),
            description=data.get('description', ''),
            special_ability=data.get('special_ability', ''),
            stat_bonuses=stat_bonuses,
            starting_jutsu=starting_jutsu,
            special_techniques=special_techniques,
            available_kekkei_genkai=available_kekkei_genkai,
            emblem_url=data.get('emblem_url', ''),
            color=data.get('color', 0),
            properties=properties
        )
    
    def to_json(self) -> str:
        """Convert clan to JSON string.
        
        Returns:
            JSON string representation of the clan
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Clan':
        """Create a clan from a JSON string.
        
        Args:
            json_str: JSON string to create clan from
            
        Returns:
            A new Clan instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def get_stat_bonus(self, stat_name: str) -> int:
        """Get the bonus for a specific stat.
        
        Args:
            stat_name: The name of the stat
            
        Returns:
            The bonus value, or 0 if not found
        """
        return self.stat_bonuses.get(stat_name, 0)
    
    def set_stat_bonus(self, stat_name: str, value: int) -> None:
        """Set the bonus for a specific stat.
        
        Args:
            stat_name: The name of the stat
            value: The bonus value
        """
        self.stat_bonuses[stat_name] = value
    
    def add_starting_jutsu(self, jutsu_name: str) -> bool:
        """Add a jutsu to the clan's starting jutsu.
        
        Args:
            jutsu_name: The name of the jutsu
            
        Returns:
            True if the jutsu was added, False if already present
        """
        if jutsu_name in self.starting_jutsu:
            return False
        
        self.starting_jutsu.append(jutsu_name)
        return True
    
    def remove_starting_jutsu(self, jutsu_name: str) -> bool:
        """Remove a jutsu from the clan's starting jutsu.
        
        Args:
            jutsu_name: The name of the jutsu
            
        Returns:
            True if the jutsu was removed, False if not found
        """
        if jutsu_name not in self.starting_jutsu:
            return False
        
        self.starting_jutsu.remove(jutsu_name)
        return True
    
    def add_special_technique(self, technique_name: str) -> bool:
        """Add a special technique to the clan.
        
        Args:
            technique_name: The name of the technique
            
        Returns:
            True if the technique was added, False if already present
        """
        if technique_name in self.special_techniques:
            return False
        
        self.special_techniques.append(technique_name)
        return True
    
    def remove_special_technique(self, technique_name: str) -> bool:
        """Remove a special technique from the clan.
        
        Args:
            technique_name: The name of the technique
            
        Returns:
            True if the technique was removed, False if not found
        """
        if technique_name not in self.special_techniques:
            return False
        
        self.special_techniques.remove(technique_name)
        return True 