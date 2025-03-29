import pytest
import discord
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from battle_manager import BattleManager

@pytest.mark.asyncio
async def test_battle_flow():
    # Create mock objects
    mock_user = discord.Object(id=123)
    mock_channel = discord.Object(id=456)
    
    # Initialize battle manager
    battle_manager = BattleManager()
    
    # Test starting a battle
    start_message = await battle_manager.start_battle(mock_user, mock_channel)
    assert "You have encountered Solomon in God Mode!" in start_message
    
    # Test attack action
    attack_result = await battle_manager.handle_action(mock_user, mock_channel, "attack")
    assert "You attack Solomon!" in attack_result
    assert "Solomon counterattacks!" in attack_result
    
    # Test defend action
    defend_result = await battle_manager.handle_action(mock_user, mock_channel, "defend")
    assert "You defend against Solomon's attack!" in defend_result
    
    # Test using an item
    item_result = await battle_manager.handle_action(mock_user, mock_channel, "use item")
    assert "You use a healing potion!" in item_result
    
    # Test retreat
    retreat_result = await battle_manager.handle_action(mock_user, mock_channel, "retreat")
    assert "You have retreated from the battle!" in retreat_result 