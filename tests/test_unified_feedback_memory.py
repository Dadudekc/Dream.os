import os
import sys
import unittest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.UnifiedFeedbackMemory import UnifiedFeedbackMemory

class TestUnifiedFeedbackMemory(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        # Create test output directory
        self.test_output_dir = os.path.join(os.path.dirname(__file__), "test_output")
        os.makedirs(self.test_output_dir, exist_ok=True)
        
        # Initialize UnifiedFeedbackMemory
        self.feedback_memory = UnifiedFeedbackMemory(
            memory_dir=self.test_output_dir,
            max_entries=1000,
            retention_days=7
        )
        
        # Test data
        self.test_memory = {
            "id": "test_memory_1",
            "timestamp": datetime.now().isoformat(),
            "type": "user_interaction",
            "data": {
                "user_id": "test_user_1",
                "action": "message_sent",
                "content": "Test message content",
                "context": {
                    "channel_id": "test_channel_1",
                    "message_id": "test_message_1"
                }
            }
        }
    
    def test_initialization(self):
        """Test if UnifiedFeedbackMemory initializes correctly."""
        self.assertIsNotNone(self.feedback_memory)
        self.assertEqual(self.feedback_memory.max_entries, 1000)
        self.assertEqual(self.feedback_memory.retention_days, 7)
        self.assertTrue(os.path.exists(self.feedback_memory.memory_dir))
        self.assertIsNotNone(self.feedback_memory.logger)
    
    def test_store_memory(self):
        """Test memory storage functionality."""
        # Store memory
        memory_id = self.feedback_memory.store_memory(self.test_memory)
        
        # Verify memory was stored
        self.assertEqual(memory_id, "test_memory_1")
        self.assertIn(memory_id, self.feedback_memory.memory_data)
        self.assertEqual(self.feedback_memory.memory_data[memory_id]["type"], "user_interaction")
    
    def test_get_memory(self):
        """Test memory retrieval functionality."""
        # Store memory
        memory_id = self.feedback_memory.store_memory(self.test_memory)
        
        # Get memory
        memory = self.feedback_memory.get_memory(memory_id)
        
        # Verify memory data
        self.assertEqual(memory["id"], memory_id)
        self.assertEqual(memory["type"], "user_interaction")
        self.assertEqual(memory["data"]["action"], "message_sent")
    
    def test_update_memory(self):
        """Test memory update functionality."""
        # Store memory
        memory_id = self.feedback_memory.store_memory(self.test_memory)
        
        # Update memory
        update_data = {
            "data": {
                "content": "Updated message content",
                "action": "message_edited"
            }
        }
        self.feedback_memory.update_memory(memory_id, update_data)
        
        # Verify update
        memory = self.feedback_memory.get_memory(memory_id)
        self.assertEqual(memory["data"]["content"], "Updated message content")
        self.assertEqual(memory["data"]["action"], "message_edited")
    
    def test_delete_memory(self):
        """Test memory deletion functionality."""
        # Store memory
        memory_id = self.feedback_memory.store_memory(self.test_memory)
        
        # Delete memory
        self.feedback_memory.delete_memory(memory_id)
        
        # Verify deletion
        self.assertNotIn(memory_id, self.feedback_memory.memory_data)
        with self.assertRaises(KeyError):
            self.feedback_memory.get_memory(memory_id)
    
    def test_list_memories(self):
        """Test memory listing functionality."""
        # Store multiple memories
        memory_entries = []
        for i in range(3):
            memory = self.test_memory.copy()
            memory["id"] = f"test_memory_{i}"
            memory["data"]["action"] = f"action_{i}"
            memory_entries.append(self.feedback_memory.store_memory(memory))
        
        # List memories
        memory_list = self.feedback_memory.list_memories()
        
        # Verify list
        self.assertEqual(len(memory_list), 3)
        self.assertEqual(len(memory_entries), 3)
    
    def test_search_memories(self):
        """Test memory search functionality."""
        # Store memories with different content
        contents = ["test message", "important message", "urgent message"]
        for content in contents:
            memory = self.test_memory.copy()
            memory["id"] = f"test_memory_{content}"
            memory["data"]["content"] = content
            self.feedback_memory.store_memory(memory)
        
        # Search memories
        search_results = self.feedback_memory.search_memories("important")
        
        # Verify search
        self.assertEqual(len(search_results), 1)
        self.assertEqual(search_results[0]["data"]["content"], "important message")
    
    def test_retrieve_memories(self):
        """Test memory retrieval with filters."""
        # Store memories with different timestamps
        timestamps = [
            datetime.now() - timedelta(days=1),
            datetime.now(),
            datetime.now() + timedelta(days=1)
        ]
        
        for timestamp in timestamps:
            memory = self.test_memory.copy()
            memory["id"] = f"test_memory_{timestamp.isoformat()}"
            memory["timestamp"] = timestamp.isoformat()
            self.feedback_memory.store_memory(memory)
        
        # Retrieve memories
        memories = self.feedback_memory.retrieve_memories(
            start_time=(datetime.now() - timedelta(days=2)).isoformat(),
            end_time=(datetime.now() + timedelta(days=2)).isoformat()
        )
        
        # Verify retrieval
        self.assertEqual(len(memories), 3)
    
    def test_cleanup_old_memories(self):
        """Test old memory cleanup functionality."""
        # Store old memory
        old_memory = self.test_memory.copy()
        old_memory["timestamp"] = (datetime.now() - timedelta(days=8)).isoformat()
        self.feedback_memory.store_memory(old_memory)
        
        # Store recent memory
        recent_memory = self.test_memory.copy()
        recent_memory["id"] = "recent_memory"
        recent_memory["timestamp"] = datetime.now().isoformat()
        self.feedback_memory.store_memory(recent_memory)
        
        # Cleanup old memories
        self.feedback_memory.cleanup_old_memories()
        
        # Verify cleanup
        self.assertNotIn("test_memory_1", self.feedback_memory.memory_data)
        self.assertIn("recent_memory", self.feedback_memory.memory_data)
    
    def test_memory_compression(self):
        """Test memory compression functionality."""
        # Create large memory
        large_memory = self.test_memory.copy()
        large_memory["data"]["content"] = "x" * 1000  # Large content
        
        # Store memory with compression
        memory_id = self.feedback_memory.store_memory(large_memory, compress=True)
        
        # Verify compression
        memory = self.feedback_memory.get_memory(memory_id)
        self.assertIn("compressed", memory)
        self.assertTrue(memory["compressed"])
    
    def test_memory_validation(self):
        """Test memory validation functionality."""
        # Create invalid memory
        invalid_memory = {
            "id": "test_memory_2",
            "type": "user_interaction"
            # Missing required fields
        }
        
        # Verify validation
        with self.assertRaises(ValueError):
            self.feedback_memory.store_memory(invalid_memory)
    
    def test_memory_aggregation(self):
        """Test memory aggregation functionality."""
        # Store memories with different types
        types = ["user_interaction", "system_event", "error_log"]
        for type_name in types:
            memory = self.test_memory.copy()
            memory["id"] = f"test_memory_{type_name}"
            memory["type"] = type_name
            self.feedback_memory.store_memory(memory)
        
        # Aggregate memories
        aggregation = self.feedback_memory.aggregate_memories()
        
        # Verify aggregation
        self.assertIn("user_interaction", aggregation)
        self.assertIn("system_event", aggregation)
        self.assertIn("error_log", aggregation)
    
    def test_memory_export(self):
        """Test memory export functionality."""
        # Store memory
        self.feedback_memory.store_memory(self.test_memory)
        
        # Export memory
        export_path = self.feedback_memory.export_memories()
        
        # Verify export
        self.assertTrue(os.path.exists(export_path))
        
        with open(export_path, 'r') as f:
            export_data = json.load(f)
            self.assertEqual(len(export_data), 1)
            self.assertEqual(export_data[0]["id"], "test_memory_1")
    
    def test_memory_import(self):
        """Test memory import functionality."""
        # Create test export data
        export_data = [self.test_memory]
        export_path = os.path.join(self.test_output_dir, "test_export.json")
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f)
        
        # Import memory
        self.feedback_memory.import_memories(export_path)
        
        # Verify import
        memory = self.feedback_memory.get_memory("test_memory_1")
        self.assertEqual(memory["type"], "user_interaction")
        self.assertEqual(memory["data"]["action"], "message_sent")
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove test output directory
        if os.path.exists(self.test_output_dir):
            for file in os.listdir(self.test_output_dir):
                os.remove(os.path.join(self.test_output_dir, file))
            os.rmdir(self.test_output_dir)

if __name__ == '__main__':
    unittest.main() 
