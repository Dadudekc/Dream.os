"""Character model for the RPG system.

This module provides a standalone Character class that can be used
in any RPG system that requires character management.
"""
from typing import Dict, List, Any, Optional
import uuid
import json
import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class Character:
    """Character model for the RPG system."""
    
    # Basic information
    name: str
    clan: str = "Civilian"
    
    # Identifier (UUID if not specified)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Progression
    level: int = 1
    exp: int = 0
    rank: str = "Academy Student"
    specialization: Optional[str] = None
    
    # Stats
    ninjutsu: int = 10
    taijutsu: int = 10
    genjutsu: int = 10
    intelligence: int = 10
    strength: int = 10
    speed: int = 10
    stamina: int = 10
    chakra_control: int = 10
    perception: int = 10
    willpower: int = 10
    
    # Resources
    hp: int = 100
    max_hp: int = 100
    chakra: int = 100
    max_chakra: int = 100
    
    # Inventory and abilities
    inventory: Dict[str, List[str]] = field(default_factory=lambda: {
        "weapons": [],
        "equipment": [],
        "consumables": []
    })
    
    jutsu: List[str] = field(default_factory=list)
    
    # Status effects
    active_effects: List[str] = field(default_factory=list)
    status_conditions: List[str] = field(default_factory=list)
    buffs: List[str] = field(default_factory=list)
    debuffs: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    
    def __post_init__(self):
        """Initialize derived properties after creation."""
        # Set default HP and chakra based on level and stats
        if self.max_hp == 100:
            self.max_hp = 100 + (self.level * 10) + (self.stamina * 5)
            self.hp = self.max_hp
        
        if self.max_chakra == 100:
            self.max_chakra = 100 + (self.level * 10) + (self.chakra_control * 5)
            self.chakra = self.max_chakra
    
    @property
    def stats(self) -> Dict[str, int]:
        """Get character stats as a dictionary.
        
        Returns:
            Dictionary of stat names and values
        """
        return {
            "ninjutsu": self.ninjutsu,
            "taijutsu": self.taijutsu,
            "genjutsu": self.genjutsu,
            "intelligence": self.intelligence,
            "strength": self.strength,
            "speed": self.speed,
            "stamina": self.stamina,
            "chakra_control": self.chakra_control,
            "perception": self.perception,
            "willpower": self.willpower
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert character to a dictionary.
        
        Returns:
            Dictionary representation of the character
        """
        # Update the updated_at timestamp
        self.updated_at = datetime.datetime.now().isoformat()
        
        # Return as dictionary
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Character':
        """Create a character from a dictionary.
        
        Args:
            data: Dictionary data to create character from
            
        Returns:
            A new Character instance
        """
        # Handle nested dictionaries and lists
        inventory = data.get('inventory', {})
        if isinstance(inventory, dict):
            # Ensure all inventory categories exist
            for category in ['weapons', 'equipment', 'consumables']:
                if category not in inventory:
                    inventory[category] = []
        else:
            # If inventory is not a dict, create a default one
            inventory = {
                "weapons": [],
                "equipment": [],
                "consumables": []
            }
        
        # Replace inventory in data
        data['inventory'] = inventory
        
        # Create character instance
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert character to JSON string.
        
        Returns:
            JSON string representation of the character
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Character':
        """Create a character from a JSON string.
        
        Args:
            json_str: JSON string to create character from
            
        Returns:
            A new Character instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def add_exp(self, amount: int) -> bool:
        """Add experience points to the character.
        
        Args:
            amount: Amount of experience to add
            
        Returns:
            True if the character leveled up, False otherwise
        """
        if amount <= 0:
            return False
        
        self.exp += amount
        level_up = False
        
        # Check for level up
        while self.exp >= self.level * 100:
            self.exp -= self.level * 100
            self.level += 1
            
            # Update max HP and chakra
            self.max_hp = 100 + (self.level * 10) + (self.stamina * 5)
            self.max_chakra = 100 + (self.level * 10) + (self.chakra_control * 5)
            
            level_up = True
        
        # Update timestamp
        self.updated_at = datetime.datetime.now().isoformat()
        
        return level_up
    
    def add_item(self, category: str, item: str) -> bool:
        """Add an item to the character's inventory.
        
        Args:
            category: The category to add the item to (weapons, equipment, consumables)
            item: The name of the item
            
        Returns:
            True if the item was added, False otherwise
        """
        if category not in self.inventory:
            self.inventory[category] = []
        
        self.inventory[category].append(item)
        
        # Update timestamp
        self.updated_at = datetime.datetime.now().isoformat()
        
        return True
    
    def remove_item(self, category: str, item: str) -> bool:
        """Remove an item from the character's inventory.
        
        Args:
            category: The category to remove the item from
            item: The name of the item
            
        Returns:
            True if the item was removed, False otherwise
        """
        if category not in self.inventory or item not in self.inventory[category]:
            return False
        
        self.inventory[category].remove(item)
        
        # Update timestamp
        self.updated_at = datetime.datetime.now().isoformat()
        
        return True
    
    def learn_jutsu(self, jutsu_name: str) -> bool:
        """Learn a new jutsu.
        
        Args:
            jutsu_name: The name of the jutsu to learn
            
        Returns:
            True if the jutsu was learned, False if already known
        """
        if jutsu_name in self.jutsu:
            return False
        
        self.jutsu.append(jutsu_name)
        
        # Update timestamp
        self.updated_at = datetime.datetime.now().isoformat()
        
        return True
    
    def forget_jutsu(self, jutsu_name: str) -> bool:
        """Remove a jutsu from the character's known jutsu.
        
        Args:
            jutsu_name: The name of the jutsu to forget
            
        Returns:
            True if the jutsu was forgotten, False if not known
        """
        if jutsu_name not in self.jutsu:
            return False
        
        self.jutsu.remove(jutsu_name)
        
        # Update timestamp
        self.updated_at = datetime.datetime.now().isoformat()
        
        return True
    
    def add_status(self, status: str, status_type: str = "status_conditions") -> bool:
        """Add a status effect to the character.
        
        Args:
            status: The status effect to add
            status_type: The type of status (status_conditions, active_effects, buffs, debuffs)
            
        Returns:
            True if the status was added, False otherwise
        """
        if status_type not in ["status_conditions", "active_effects", "buffs", "debuffs"]:
            return False
        
        status_list = getattr(self, status_type)
        if status in status_list:
            return False
        
        status_list.append(status)
        
        # Update timestamp
        self.updated_at = datetime.datetime.now().isoformat()
        
        return True
    
    def remove_status(self, status: str, status_type: str = "status_conditions") -> bool:
        """Remove a status effect from the character.
        
        Args:
            status: The status effect to remove
            status_type: The type of status (status_conditions, active_effects, buffs, debuffs)
            
        Returns:
            True if the status was removed, False otherwise
        """
        if status_type not in ["status_conditions", "active_effects", "buffs", "debuffs"]:
            return False
        
        status_list = getattr(self, status_type)
        if status not in status_list:
            return False
        
        status_list.remove(status)
        
        # Update timestamp
        self.updated_at = datetime.datetime.now().isoformat()
        
        return True
    
    def heal(self, amount: int) -> int:
        """Heal the character by the specified amount.
        
        Args:
            amount: The amount to heal
            
        Returns:
            The actual amount healed
        """
        if amount <= 0:
            return 0
        
        old_hp = self.hp
        self.hp = min(self.hp + amount, self.max_hp)
        
        # Update timestamp
        self.updated_at = datetime.datetime.now().isoformat()
        
        return self.hp - old_hp
    
    def damage(self, amount: int) -> int:
        """Damage the character by the specified amount.
        
        Args:
            amount: The amount of damage to deal
            
        Returns:
            The actual amount of damage dealt
        """
        if amount <= 0:
            return 0
        
        old_hp = self.hp
        self.hp = max(self.hp - amount, 0)
        
        # Update timestamp
        self.updated_at = datetime.datetime.now().isoformat()
        
        return old_hp - self.hp
    
    def restore_chakra(self, amount: int) -> int:
        """Restore the character's chakra by the specified amount.
        
        Args:
            amount: The amount of chakra to restore
            
        Returns:
            The actual amount of chakra restored
        """
        if amount <= 0:
            return 0
        
        old_chakra = self.chakra
        self.chakra = min(self.chakra + amount, self.max_chakra)
        
        # Update timestamp
        self.updated_at = datetime.datetime.now().isoformat()
        
        return self.chakra - old_chakra
    
    def use_chakra(self, amount: int) -> bool:
        """Use the specified amount of chakra.
        
        Args:
            amount: The amount of chakra to use
            
        Returns:
            True if there was enough chakra, False otherwise
        """
        if amount <= 0:
            return True
        
        if self.chakra < amount:
            return False
        
        self.chakra -= amount
        
        # Update timestamp
        self.updated_at = datetime.datetime.now().isoformat()
        
        return True 