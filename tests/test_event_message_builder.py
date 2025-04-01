import os
import sys
import unittest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.EventMessageBuilder import EventMessageBuilder

class TestEventMessageBuilder(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        # Create test output directory
        self.test_output_dir = os.path.join(os.path.dirname(__file__), "test_output")
        os.makedirs(self.test_output_dir, exist_ok=True)
        
        # Initialize EventMessageBuilder
        self.message_builder = EventMessageBuilder(
            output_dir=self.test_output_dir,
            template_dir=os.path.join(os.path.dirname(__file__), "templates")
        )
        
        # Test data
        self.test_event = {
            "id": "test_event_1",
            "type": "system_event",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "message": "Test event message",
                "severity": "info",
                "source": "test_source"
            }
        }
        
        # Create test template
        self.template_dir = os.path.join(os.path.dirname(__file__), "templates")
        os.makedirs(self.template_dir, exist_ok=True)
        
        # Create test template file
        self.template_file = os.path.join(self.template_dir, "event_template.html")
        with open(self.template_file, 'w') as f:
            f.write("""
                <div class="event">
                    <h3>{{ event.type }}</h3>
                    <p>{{ event.data.message }}</p>
                    <span class="severity">{{ event.data.severity }}</span>
                </div>
            """)
    
    def test_initialization(self):
        """Test if EventMessageBuilder initializes correctly."""
        self.assertIsNotNone(self.message_builder)
        self.assertTrue(os.path.exists(self.message_builder.output_dir))
        self.assertTrue(os.path.exists(self.message_builder.template_dir))
        self.assertIsNotNone(self.message_builder.logger)
    
    def test_build_message(self):
        """Test basic message building functionality."""
        # Build message
        message = self.message_builder.build_message(self.test_event)
        
        # Verify message structure
        self.assertIsInstance(message, dict)
        self.assertIn("content", message)
        self.assertIn("metadata", message)
        self.assertEqual(message["metadata"]["event_id"], "test_event_1")
    
    def test_build_message_with_template(self):
        """Test message building with template."""
        # Build message with template
        message = self.message_builder.build_message(
            self.test_event,
            template_name="event_template.html"
        )
        
        # Verify message content
        self.assertIn("Test event message", message["content"])
        self.assertIn("info", message["content"])
    
    def test_build_message_with_custom_format(self):
        """Test message building with custom format."""
        # Define custom format
        custom_format = {
            "title": "{{ event.type }}",
            "body": "{{ event.data.message }}",
            "footer": "Severity: {{ event.data.severity }}"
        }
        
        # Build message with custom format
        message = self.message_builder.build_message(
            self.test_event,
            custom_format=custom_format
        )
        
        # Verify message content
        self.assertIn("system_event", message["content"])
        self.assertIn("Test event message", message["content"])
        self.assertIn("Severity: info", message["content"])
    
    def test_build_message_with_attachments(self):
        """Test message building with attachments."""
        # Create test attachment
        attachment = {
            "type": "image",
            "url": "https://example.com/test.jpg",
            "caption": "Test image"
        }
        
        # Build message with attachment
        message = self.message_builder.build_message(
            self.test_event,
            attachments=[attachment]
        )
        
        # Verify attachment
        self.assertIn("attachments", message)
        self.assertEqual(len(message["attachments"]), 1)
        self.assertEqual(message["attachments"][0]["type"], "image")
    
    def test_build_message_with_embeds(self):
        """Test message building with embeds."""
        # Create test embed
        embed = {
            "title": "Event Details",
            "description": "{{ event.data.message }}",
            "color": "0x00ff00"
        }
        
        # Build message with embed
        message = self.message_builder.build_message(
            self.test_event,
            embeds=[embed]
        )
        
        # Verify embed
        self.assertIn("embeds", message)
        self.assertEqual(len(message["embeds"]), 1)
        self.assertEqual(message["embeds"][0]["title"], "Event Details")
    
    def test_build_message_with_actions(self):
        """Test message building with actions."""
        # Create test actions
        actions = [
            {
                "type": "button",
                "label": "View Details",
                "action": "view_event",
                "data": {"event_id": "test_event_1"}
            }
        ]
        
        # Build message with actions
        message = self.message_builder.build_message(
            self.test_event,
            actions=actions
        )
        
        # Verify actions
        self.assertIn("actions", message)
        self.assertEqual(len(message["actions"]), 1)
        self.assertEqual(message["actions"][0]["label"], "View Details")
    
    def test_build_message_with_metadata(self):
        """Test message building with metadata."""
        # Create test metadata
        metadata = {
            "category": "system",
            "tags": ["test", "event"],
            "priority": "high"
        }
        
        # Build message with metadata
        message = self.message_builder.build_message(
            self.test_event,
            metadata=metadata
        )
        
        # Verify metadata
        self.assertIn("metadata", message)
        self.assertEqual(message["metadata"]["category"], "system")
        self.assertEqual(message["metadata"]["tags"], ["test", "event"])
    
    def test_build_message_with_validation(self):
        """Test message building with validation."""
        # Create invalid event
        invalid_event = {
            "id": "test_event_2",
            "type": "system_event"
            # Missing required fields
        }
        
        # Build message with validation
        with self.assertRaises(ValueError):
            self.message_builder.build_message(invalid_event)
    
    def test_build_message_with_localization(self):
        """Test message building with localization."""
        # Create localized event
        localized_event = self.test_event.copy()
        localized_event["data"]["message"] = "Test message"
        localized_event["locale"] = "es"
        
        # Build message with localization
        message = self.message_builder.build_message(localized_event)
        
        # Verify localization
        self.assertIn("locale", message["metadata"])
        self.assertEqual(message["metadata"]["locale"], "es")
    
    def test_build_message_with_compression(self):
        """Test message building with compression."""
        # Create large event
        large_event = self.test_event.copy()
        large_event["data"]["message"] = "x" * 1000  # Large message
        
        # Build message with compression
        message = self.message_builder.build_message(
            large_event,
            compress=True
        )
        
        # Verify compression
        self.assertIn("compressed", message["metadata"])
        self.assertTrue(message["metadata"]["compressed"])
    
    def test_save_message(self):
        """Test message saving functionality."""
        # Build message
        message = self.message_builder.build_message(self.test_event)
        
        # Save message
        file_path = self.message_builder.save_message(message)
        
        # Verify file exists
        self.assertTrue(os.path.exists(file_path))
        
        # Verify file content
        with open(file_path, 'r') as f:
            saved_content = json.load(f)
            self.assertEqual(saved_content["metadata"]["event_id"], "test_event_1")
    
    def test_load_message(self):
        """Test message loading functionality."""
        # Build and save message
        message = self.message_builder.build_message(self.test_event)
        file_path = self.message_builder.save_message(message)
        
        # Load message
        loaded_message = self.message_builder.load_message(file_path)
        
        # Verify loaded message
        self.assertEqual(loaded_message["metadata"]["event_id"], "test_event_1")
        self.assertEqual(loaded_message["content"], message["content"])
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove test output directory
        if os.path.exists(self.test_output_dir):
            for file in os.listdir(self.test_output_dir):
                os.remove(os.path.join(self.test_output_dir, file))
            os.rmdir(self.test_output_dir)
        
        # Remove test template directory
        if os.path.exists(self.template_dir):
            os.remove(self.template_file)
            os.rmdir(self.template_dir)

if __name__ == '__main__':
    unittest.main() 
