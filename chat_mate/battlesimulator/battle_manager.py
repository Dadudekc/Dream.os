import asyncio
from typing import Dict, Any, Callable

class BattleManager:
    def __init__(self):
        self.active_battles: Dict[str, Dict[str, Any]] = {}

    async def start_battle(self, user_id: str, send_message: Callable):
        """Start a battle session for a user"""
        self.active_battles[user_id] = {
            "stage": 0,
            "health": 100,
            "chakra": 100
        }
        
        await send_message("You have encountered Solomon in God Mode! This battle cannot be won, but you can try your best!")
        
        while True:
            await send_message("Choose your action:\n1. Attack\n2. Defend\n3. Use Item\n4. Retreat")
            
            try:
                response = await self._wait_for_response(user_id)
                
                if response == "1":
                    await send_message("You attack Solomon! He takes no damage, but you feel the pressure!")
                elif response == "2":
                    await send_message("You defend yourself! Solomon smirks, knowing he cannot be beaten.")
                elif response == "3":
                    await send_message("You use an item! It has no effect on Solomon.")
                elif response == "4":
                    await send_message("You decide to retreat. Solomon lets you go, but the encounter haunts you.")
                    break
                else:
                    await send_message("Invalid choice! Please select a valid action.")
                    
            except asyncio.TimeoutError:
                await send_message("You took too long to respond! The battle continues...")
    
    async def _wait_for_response(self, user_id: str) -> str:
        """Simulate waiting for user response in tests"""
        return "1"  # Default to attack for testing
