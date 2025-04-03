"""Module check script.

This script checks that all modules are working correctly by
instantiating and initializing each module.
"""
import os
import logging
from typing import Dict, Any

# Import module interfaces
from dream_modules.core.module_interface import ModuleInterface, ServiceInterface
from dream_modules.core.service_container import ServiceContainer, get_container

# Import modules
from dream_modules.modules.character.character_model import Character
from dream_modules.modules.character.character_manager import CharacterManager
from dream_modules.modules.clan.clan_model import Clan
from dream_modules.modules.clan.clan_manager import ClanManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_test_dirs():
    """Set up test directories."""
    os.makedirs("test_data/characters", exist_ok=True)
    os.makedirs("test_data/clans", exist_ok=True)
    logger.info("Created test directories")


def check_character_model():
    """Check the Character model."""
    logger.info("Testing Character model...")
    
    # Create a character
    character = Character(
        name="Test Character",
        clan="Test Clan",
        level=5,
        exp=50,
        ninjutsu=15,
        taijutsu=15,
        genjutsu=15
    )
    
    # Check properties
    assert character.name == "Test Character"
    assert character.clan == "Test Clan"
    assert character.level == 5
    assert character.exp == 50
    
    # Check methods
    character.add_exp(50)
    assert character.level == 5
    assert character.exp == 100
    
    character.add_exp(100)
    assert character.level == 6
    assert character.exp == 0
    
    # Convert to dictionary and back
    character_dict = character.to_dict()
    character2 = Character.from_dict(character_dict)
    assert character2.name == character.name
    assert character2.clan == character.clan
    assert character2.level == character.level
    
    logger.info("Character model test passed")


def check_clan_model():
    """Check the Clan model."""
    logger.info("Testing Clan model...")
    
    # Create a clan
    clan = Clan(
        name="Test Clan",
        rarity="Common",
        lore="A test clan for testing",
        special_ability="Test ability",
        stat_bonuses={"strength": 5, "intelligence": 3}
    )
    
    # Check properties
    assert clan.name == "Test Clan"
    assert clan.rarity == "Common"
    assert clan.lore == "A test clan for testing"
    
    # Check methods
    assert clan.get_stat_bonus("strength") == 5
    assert clan.get_stat_bonus("intelligence") == 3
    assert clan.get_stat_bonus("nonexistent") == 0
    
    clan.add_starting_jutsu("Test Jutsu")
    assert "Test Jutsu" in clan.starting_jutsu
    
    # Convert to dictionary and back
    clan_dict = clan.to_dict()
    clan2 = Clan.from_dict(clan_dict)
    assert clan2.name == clan.name
    assert clan2.rarity == clan.rarity
    assert clan2.get_stat_bonus("strength") == clan.get_stat_bonus("strength")
    
    logger.info("Clan model test passed")


def check_character_manager():
    """Check the CharacterManager service."""
    logger.info("Testing CharacterManager service...")
    
    # Create character manager
    manager = CharacterManager("test_data/characters")
    
    # Initialize
    config = {
        "data_dir": "test_data/characters",
        "auto_save": True,
    }
    success = manager.initialize(config)
    assert success, "Character manager initialization failed"
    
    # Check properties
    assert manager.name == "character_manager"
    assert manager.version != ""
    assert manager.description != ""
    
    # Create a character
    character_data = {
        "name": "Test Character",
        "clan": "Test Clan",
        "level": 1,
        "exp": 0,
    }
    character = manager.create_character("test_user", character_data)
    assert character is not None
    assert character.name == "Test Character"
    
    # Get the character
    character2 = manager.get_character("test_user")
    assert character2 is not None
    assert character2.name == character.name
    
    # Update the character
    update_data = {
        "level": 5,
        "exp": 50,
    }
    character3 = manager.update_character("test_user", update_data)
    assert character3 is not None
    assert character3.level == 5
    assert character3.exp == 50
    
    # Delete the character
    success = manager.delete_character("test_user")
    assert success
    
    # Shutdown
    success = manager.shutdown()
    assert success
    
    logger.info("CharacterManager service test passed")


def check_clan_manager():
    """Check the ClanManager service."""
    logger.info("Testing ClanManager service...")
    
    # Create clan manager
    manager = ClanManager("test_data/clans")
    
    # Initialize
    config = {
        "data_dir": "test_data/clans",
        "auto_save": True,
    }
    success = manager.initialize(config)
    assert success, "Clan manager initialization failed"
    
    # Check properties
    assert manager.name == "clan_manager"
    assert manager.version != ""
    assert manager.description != ""
    
    # Create some clans
    clan_data = {
        "name": "Test Clan",
        "rarity": "Common",
        "lore": "A test clan for testing",
    }
    clan = manager.create_clan(clan_data)
    assert clan is not None
    assert clan.name == "Test Clan"
    
    clan_data2 = {
        "name": "Test Clan 2",
        "rarity": "Rare",
        "lore": "Another test clan",
    }
    clan2 = manager.create_clan(clan_data2)
    assert clan2 is not None
    
    # Get a clan
    clan3 = manager.get_clan("Test Clan")
    assert clan3 is not None
    assert clan3.name == "Test Clan"
    
    # Get clans by rarity
    rare_clans = manager.get_clans_by_rarity("Rare")
    assert len(rare_clans) == 1
    assert rare_clans[0].name == "Test Clan 2"
    
    # Update a clan
    update_data = {
        "rarity": "Epic",
        "special_ability": "Test ability",
    }
    clan4 = manager.update_clan("Test Clan", update_data)
    assert clan4 is not None
    assert clan4.rarity == "Epic"
    assert clan4.special_ability == "Test ability"
    
    # Delete a clan
    success = manager.delete_clan("Test Clan")
    assert success
    
    # Shutdown
    success = manager.shutdown()
    assert success
    
    logger.info("ClanManager service test passed")


def check_service_container():
    """Check the ServiceContainer."""
    logger.info("Testing ServiceContainer...")
    
    # Get container
    container = get_container()
    
    # Clear container
    container.clear()
    
    # Create test service
    class TestService:
        def get_name(self):
            return "TestService"
    
    # Register service
    success = container.register("test_service", TestService())
    assert success
    
    # Check if service exists
    assert container.has("test_service")
    
    # Get service
    service = container.get("test_service")
    assert service is not None
    assert service.get_name() == "TestService"
    
    # Register factory
    success = container.register_factory("factory_service", lambda: TestService())
    assert success
    
    # Get service from factory
    service2 = container.get("factory_service")
    assert service2 is not None
    assert service2.get_name() == "TestService"
    
    # Remove service
    success = container.remove("test_service")
    assert success
    assert not container.has("test_service")
    
    # Clear container
    container.clear()
    assert not container.has("factory_service")
    
    logger.info("ServiceContainer test passed")


def main():
    """Run all module checks."""
    logger.info("Starting module checks...")
    
    try:
        # Set up test directories
        setup_test_dirs()
        
        # Check modules
        check_character_model()
        check_clan_model()
        check_character_manager()
        check_clan_manager()
        check_service_container()
        
        logger.info("All module checks passed!")
    except AssertionError as e:
        logger.error(f"Module check failed: {e}")
    except Exception as e:
        logger.error(f"Error during module checks: {e}", exc_info=True)


if __name__ == "__main__":
    main() 