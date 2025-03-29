import os
import sys
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.AletheiaPromptManager import AletheiaPromptManager

class TestMemoryCycle(unittest.TestCase):
    def setUp(self):
        """Set up test environment with temporary memory files."""
        self.test_memory_dir = project_root / "tests" / "test_memory"
        self.test_memory_dir.mkdir(exist_ok=True)
        
        self.memory_file = self.test_memory_dir / "test_persistent_memory.json"
        self.prompt_manager = AletheiaPromptManager(
            memory_file=str(self.memory_file)
        )

    def tearDown(self):
        """Clean up test files."""
        for file in self.test_memory_dir.glob("*.json"):
            file.unlink()
        self.test_memory_dir.rmdir()

    def test_conversation_cycle(self):
        """Test a complete conversation cycle with memory updates."""
        # Start a test cycle
        cycle_id = self.prompt_manager.start_conversation_cycle("test_cycle")
        self.assertIsNotNone(cycle_id)
        
        # Simulate a dreamscape conversation
        mock_response = '''
        The Architect ventures into the depths of the Code Caverns, wielding the newly forged Debugger's Blade. 
        Ancient protocols awaken as the system's core resonates with newfound power.
        
        MEMORY_UPDATE:
        {
            "skill_level_advancements": ["Debug Mastery Level 3"],
            "newly_stabilized_domains": ["Code Caverns"],
            "newly_unlocked_protocols": ["Ancient Debug Protocol"],
            "quest_completions": ["Core Resonance Quest"],
            "architect_tier_progression": "Journeyman -> Expert"
        }
        '''
        
        # Record the conversation
        conv_id = self.prompt_manager.record_conversation(cycle_id, "dreamscape", mock_response)
        self.assertIsNotNone(conv_id)
        
        # Verify conversation was recorded
        self.assertIn(conv_id, [conv["id"] for conv in self.prompt_manager.conversation_memory["conversations"]])
        
        # End the cycle
        self.prompt_manager.end_conversation_cycle(cycle_id)
        
        # Verify memory was updated
        memory_state = self.prompt_manager.memory_state
        self.assertIn("data", memory_state)
        data = memory_state["data"]
        
        # Check specific memory updates
        self.assertIn("Debug Mastery Level 3", data.get("skill_level_advancements", []))
        self.assertIn("Code Caverns", data.get("newly_stabilized_domains", []))
        
        # Test memory persistence
        # Create a new prompt manager instance
        new_prompt_manager = AletheiaPromptManager(
            memory_file=str(self.memory_file)
        )
        
        # Verify memory state persisted
        new_memory_state = new_prompt_manager.memory_state
        self.assertEqual(memory_state, new_memory_state)

    def test_multiple_cycles(self):
        """Test multiple conversation cycles with cumulative memory updates."""
        # First cycle
        cycle1_id = self.prompt_manager.start_conversation_cycle("cycle1")
        mock_response1 = '''
        The Architect discovers ancient scrolls of wisdom.
        
        MEMORY_UPDATE:
        {
            "skill_level_advancements": ["Scroll Reading Level 1"],
            "newly_stabilized_domains": ["Ancient Library"],
            "newly_unlocked_protocols": ["Scroll Decoding"],
            "quest_completions": ["Library Access Granted"],
            "architect_tier_progression": "Novice -> Apprentice"
        }
        '''
        self.prompt_manager.record_conversation(cycle1_id, "dreamscape", mock_response1)
        self.prompt_manager.end_conversation_cycle(cycle1_id)
        
        # Second cycle
        cycle2_id = self.prompt_manager.start_conversation_cycle("cycle2")
        mock_response2 = '''
        The Architect masters the ancient scrolls' teachings.
        
        MEMORY_UPDATE:
        {
            "skill_level_advancements": ["Scroll Reading Level 2"],
            "newly_stabilized_domains": ["Scroll Chamber"],
            "newly_unlocked_protocols": ["Advanced Decoding"],
            "quest_completions": ["Scroll Mastery Complete"],
            "architect_tier_progression": "Apprentice -> Adept"
        }
        '''
        self.prompt_manager.record_conversation(cycle2_id, "dreamscape", mock_response2)
        self.prompt_manager.end_conversation_cycle(cycle2_id)
        
        # Verify cumulative updates
        data = self.prompt_manager.memory_state["data"]
        self.assertIn("Scroll Reading Level 1", data.get("skill_level_advancements", []))
        self.assertIn("Scroll Reading Level 2", data.get("skill_level_advancements", []))
        self.assertEqual(data.get("architect_tier_progression"), "Apprentice -> Adept")

    def test_template_rendering(self):
        """Test template rendering with current memory state."""
        # Set up initial memory state
        cycle_id = self.prompt_manager.start_conversation_cycle("template_test")
        mock_response = '''
        The Architect begins their journey.
        
        MEMORY_UPDATE:
        {
            "skill_level_advancements": ["Basic Training Complete"],
            "architect_tier_progression": "Initiate"
        }
        '''
        self.prompt_manager.record_conversation(cycle_id, "dreamscape", mock_response)
        self.prompt_manager.end_conversation_cycle(cycle_id)
        
        # Get a new prompt
        prompt = self.prompt_manager.get_prompt("dreamscape", cycle_id)
        
        # Verify the prompt contains the current memory state
        self.assertIn("Basic Training Complete", prompt)
        self.assertIn("Initiate", prompt)

if __name__ == '__main__':
    unittest.main() 