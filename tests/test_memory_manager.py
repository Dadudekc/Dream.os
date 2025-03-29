# test_memory_manager.py

import unittest
import os
import sys
import tempfile
import shutil
import json

sys.path.append('core')
from MemoryManager import MemoryManager

class TestMemoryManager(unittest.TestCase):
    def setUp(self):
        # Create a temp directory for memory storage
        self.test_dir = tempfile.mkdtemp()
        self.memory_file = os.path.join(self.test_dir, "test_memory.json")
        self.db_file = os.path.join(self.test_dir, "test_db.sqlite")
        self.template_dir = os.path.join(self.test_dir, "templates")
        os.makedirs(self.template_dir, exist_ok=True)

        # Write dummy template for narrative rendering
        with open(os.path.join(self.template_dir, "sample_template.j2"), "w") as f:
            f.write("Hello, {{ name }}!")

        self.mm = MemoryManager(
            max_cache_size=10,
            memory_dir=self.test_dir,
            memory_file=self.memory_file,
            db_file=self.db_file,
            template_dir=self.template_dir
        )

    def tearDown(self):
        self.mm.close()
        shutil.rmtree(self.test_dir)

    def test_set_get_memory_segment(self):
        self.mm.set("test_key", {"a": 123}, segment="system")
        result = self.mm.get("test_key", segment="system")
        self.assertEqual(result, {"a": 123})

    def test_delete_and_clear_segment(self):
        self.mm.set("delete_key", {"x": 1}, segment="system")
        self.assertTrue(self.mm.delete("delete_key", segment="system"))
        self.assertIsNone(self.mm.get("delete_key", segment="system"))

        self.mm.set("clear_key", {"y": 2}, segment="system")
        self.mm.clear_segment("system")
        self.assertIsNone(self.mm.get("clear_key", segment="system"))

    def test_segment_size_and_keys(self):
        self.mm.set("k1", {"v": 1}, segment="prompts")
        self.mm.set("k2", {"v": 2}, segment="prompts")
        self.assertEqual(self.mm.get_segment_size("prompts"), 2)
        self.assertIn("k1", self.mm.get_segment_keys("prompts"))

    def test_user_history_operations(self):
        self.mm.record_interaction(
            platform="twitter",
            username="testuser",
            response="Hello world",
            sentiment="positive",
            success=True,
            interaction_id="conv1"
        )
        history = self.mm.get_user_history("twitter", "testuser")
        self.assertGreaterEqual(len(history), 1)

        summary = self.mm.user_sentiment_summary("twitter", "testuser")
        self.assertEqual(summary["sentiment_distribution"]["positive"], 1)

        self.mm.clear_user_history("twitter", "testuser")
        self.assertEqual(self.mm.get_user_history("twitter", "testuser"), [])

    def test_narrative_generation(self):
        result = self.mm.generate_narrative("sample_template.j2", {"name": "Victor"})
        self.assertIn("Victor", result)

    def test_json_memory_update(self):
        updated = self.mm.update_context("skill_levels.System Convergence", 5)
        self.assertTrue(updated)
        self.assertEqual(
            self.mm.data["skill_levels"]["System Convergence"], 5
        )

    def test_initialize_and_export_conversation(self):
        interaction_id = "conv_test"
        self.mm.initialize_conversation(interaction_id, {"topic": "test"})

        self.mm.record_interaction(
            platform="twitter",
            username="userx",
            response="Ping",
            sentiment="neutral",
            success=True,
            interaction_id=interaction_id
        )

        export_path = os.path.join(self.test_dir, "export.jsonl")
        success = self.mm.export_conversation_for_finetuning(interaction_id, export_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(export_path))

    def test_stats_reporting(self):
        self.mm.set("stat_test", {"k": 42}, segment="system")
        stats = self.mm.get_stats()
        self.assertIn("cache_size", stats)
        self.assertIn("segments", stats)

if __name__ == "__main__":
    unittest.main()
