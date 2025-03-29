import os
import sys
import json
import re
import shutil
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# Assume the module under test is located at core/AletheiaPromptManager.py
# Adjust the import path as needed.
from core.AletheiaPromptManager import AletheiaPromptManager

# Create a dummy DiscordManager that does nothing.
class DummyDiscordManager:
    def send_message(self, prompt_type: str, message: str) -> None:
        pass

class TestAletheiaPromptManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory to serve as our project root.
        self.temp_dir = tempfile.mkdtemp()
        # Create the templates/prompt_templates folder inside the temporary project root.
        self.templates_dir = os.path.join(self.temp_dir, "templates", "prompt_templates")
        os.makedirs(self.templates_dir, exist_ok=True)
        # Create the memory folder
        self.memory_dir = os.path.join(self.temp_dir, "memory")
        os.makedirs(self.memory_dir, exist_ok=True)

        # Write a dummy jinja template file for testing get_prompt and list_available_prompts.
        self.test_template_name = "test_prompt.j2"
        self.test_template_content = "Current Memory: {{ CURRENT_MEMORY_STATE }}, Timestamp: {{ TIMESTAMP }}"
        with open(os.path.join(self.templates_dir, self.test_template_name), "w", encoding="utf-8") as f:
            f.write(self.test_template_content)

        # Patch the module-level variables in AletheiaPromptManager.
        # We override ROOT_DIR, template_path and memory_path for testing.
        self.patcher_root = patch("core.AletheiaPromptManager.ROOT_DIR", new=self.temp_dir)
        self.patcher_template = patch("core.AletheiaPromptManager.template_path", new=self.templates_dir)
        self.patcher_memory = patch("core.AletheiaPromptManager.memory_path", new=self.memory_dir)
        self.patcher_root.start()
        self.patcher_template.start()
        self.patcher_memory.start()

        # Patch the DiscordManager with our dummy version.
        self.patcher_discord = patch("core.AletheiaPromptManager.DiscordManager", new=DummyDiscordManager)
        self.patcher_discord.start()

        # Create an instance of AletheiaPromptManager, using a memory file in our temp directory.
        memory_file = os.path.join("memory", "persistent_memory.json")
        self.manager = AletheiaPromptManager(memory_file=memory_file)

        # Override async save to run synchronously for testing.
        def sync_save(file_path, data, data_type):
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
        self.manager._async_save = sync_save

    def tearDown(self):
        self.patcher_root.stop()
        self.patcher_template.stop()
        self.patcher_memory.stop()
        self.patcher_discord.stop()
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)

    def test_start_conversation_cycle(self):
        # Start a new conversation cycle.
        cycle_type = "test_cycle"
        cycle_id = self.manager.start_conversation_cycle(cycle_type)
        self.assertTrue(cycle_id.startswith("cycle_"))
        # Ensure the cycle is stored in cycle_memory.
        self.assertIn(cycle_id, self.manager.cycle_memory["cycles"])
        cycle = self.manager.cycle_memory["cycles"][cycle_id]
        self.assertEqual(cycle["type"], cycle_type)
        self.assertIn("start_time", cycle)
        self.assertNotIn("end_time", cycle)

    def test_end_conversation_cycle(self):
        # Start and then end a conversation cycle.
        cycle_type = "test_cycle"
        cycle_id = self.manager.start_conversation_cycle(cycle_type)
        self.manager.end_conversation_cycle(cycle_id)
        cycle = self.manager.cycle_memory["cycles"].get(cycle_id)
        self.assertIn("end_time", cycle)

    def test_record_conversation(self):
        # Create a dummy conversation record.
        cycle_id = self.manager.start_conversation_cycle("test_record")
        prompt_type = "test"
        response = "This is a test response. MEMORY_UPDATE: {\"key\": \"value\"}"
        conv_id = self.manager.record_conversation(cycle_id, prompt_type, response)
        self.assertTrue(conv_id.startswith("conv_"))
        # Verify conversation memory has been updated.
        conversations = self.manager.conversation_memory["conversations"]
        self.assertTrue(any(conv["id"] == conv_id for conv in conversations))
        # Also check that the conversation id is appended to the cycle.
        cycle = self.manager.cycle_memory["cycles"][cycle_id]
        self.assertIn(conv_id, cycle["conversations"])

    def test_get_prompt(self):
        # Test that get_prompt correctly renders the dummy template.
        rendered = self.manager.get_prompt("test_prompt")
        self.assertIn("Current Memory:", rendered)
        self.assertIn("Timestamp:", rendered)

    def test_list_available_prompts(self):
        # List available prompts should at least include our test template (without .j2).
        available = self.manager.list_available_prompts()
        self.assertIn("test_prompt", available)

    def test_load_and_save_memory_state(self):
        # Modify the memory state and save it.
        self.manager.memory_state["data"]["test_key"] = "test_value"
        self.manager.save_memory_state()
        # Create a new instance to load from the saved file.
        new_manager = AletheiaPromptManager(memory_file=os.path.join("memory", "persistent_memory.json"))
        new_manager._async_save = lambda fp, data, dt: json.dump(data, open(fp, "w", encoding="utf-8"), indent=4)
        new_manager.load_memory_state()
        self.assertEqual(new_manager.memory_state["data"].get("test_key"), "test_value")

    def test_parse_memory_updates_and_archive_episode(self):
        # Create a temporary file simulating an episode narrative.
        episode_file = os.path.join(self.temp_dir, "test_episode.txt")
        simulated_response = (
            "EPISODE NARRATIVE:\nSome narrative text...\n"
            "MEMORY_UPDATE:\n{\"skill_advancements\": [\"Test Upgrade\"], \"new_feature\": \"Enabled\"}"
        )
        with open(episode_file, "w", encoding="utf-8") as f:
            f.write(simulated_response)
        # Capture current version for later comparison.
        current_version = self.manager.memory_state.get("version", 1)
        # Run parse_memory_updates; it should update memory and archive the file.
        self.manager.parse_memory_updates(episode_file)
        # Memory should be updated.
        self.assertIn("Test Upgrade", self.manager.memory_state["data"].get("skill_advancements", []))
        self.assertEqual(self.manager.memory_state["data"].get("new_feature"), "Enabled")
        # The memory version should have incremented.
        self.assertGreater(self.manager.memory_state["version"], current_version)
        # The file should be moved to an archive folder.
        archive_dir = os.path.join(os.path.dirname(episode_file), "archive")
        archived_file = os.path.join(archive_dir, os.path.basename(episode_file))
        self.assertTrue(os.path.exists(archived_file))
        # Cleanup the archived file.
        os.remove(archived_file)

    def test_extract_memory_update_block_valid(self):
        content = "Some text\nMEMORY_UPDATE: {\"a\": 1, \"b\": [2,3]}"
        updates = self.manager._extract_memory_update_block(content)
        self.assertEqual(updates, {"a": 1, "b": [2, 3]})

    def test_extract_memory_update_block_invalid(self):
        content = "No memory update block here."
        updates = self.manager._extract_memory_update_block(content)
        self.assertEqual(updates, {})

    def test_merge_memory_updates(self):
        # Starting with an empty memory data.
        self.manager.memory_state["data"] = {}
        updates = {
            "list_key": ["item1"],
            "dict_key": {"inner": "value"},
            "scalar_key": "initial"
        }
        self.manager._merge_memory_updates(updates)
        # Merge a second update: adding to list, updating dict and scalar.
        second_updates = {
            "list_key": ["item2", "item1"],  # item1 is duplicate
            "dict_key": {"another": "val"},
            "scalar_key": "updated"
        }
        self.manager._merge_memory_updates(second_updates)
        self.assertEqual(self.manager.memory_state["data"]["list_key"], ["item1", "item2"])
        self.assertEqual(self.manager.memory_state["data"]["dict_key"], {"inner": "value", "another": "val"})
        self.assertEqual(self.manager.memory_state["data"]["scalar_key"], "updated")

    def test_archive_episode(self):
        # Create a temporary file and then archive it.
        temp_file = os.path.join(self.temp_dir, "temp_episode.txt")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write("Test content")
        self.manager.archive_episode(temp_file)
        archive_dir = os.path.join(os.path.dirname(temp_file), "archive")
        archived_file = os.path.join(archive_dir, os.path.basename(temp_file))
        self.assertTrue(os.path.exists(archived_file))
        # Clean up.
        os.remove(archived_file)

if __name__ == "__main__":
    unittest.main()