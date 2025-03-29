import os
import sys
import unittest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.UnifiedDiscordService import UnifiedDiscordService

class TestUnifiedDiscordService(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        # Create test config directory
        self.test_config_dir = os.path.join(os.path.dirname(__file__), "test_config")
        os.makedirs(self.test_config_dir, exist_ok=True)
        
        # Create test config
        self.test_config = {
            "discord": {
                "token": "test_token",
                "guild_id": "test_guild",
                "channels": {
                    "general": "test_channel_id",
                    "announcements": "test_announcement_id"
                }
            }
        }
        
        self.test_config_path = os.path.join(self.test_config_dir, "config.json")
        with open(self.test_config_path, 'w') as f:
            json.dump(self.test_config, f)
        
        # Initialize UnifiedDiscordService
        self.discord_service = UnifiedDiscordService(
            config_path=self.test_config_path,
            dry_run=True
        )
        
        # Test data
        self.test_message = {
            "content": "Test message",
            "embeds": [{
                "title": "Test Embed",
                "description": "Test Description"
            }]
        }
    
    def test_initialization(self):
        """Test if UnifiedDiscordService initializes correctly."""
        self.assertIsNotNone(self.discord_service)
        self.assertEqual(self.discord_service.token, "test_token")
        self.assertEqual(self.discord_service.guild_id, "test_guild")
        self.assertTrue(self.discord_service.dry_run)
    
    def test_get_channel(self):
        """Test channel retrieval."""
        # Test getting existing channel
        channel = self.discord_service.get_channel("general")
        self.assertEqual(channel, "test_channel_id")
        
        # Test getting non-existent channel
        channel = self.discord_service.get_channel("nonexistent")
        self.assertIsNone(channel)
    
    def test_send_message(self):
        """Test message sending."""
        # Mock Discord client
        self.discord_service.client = AsyncMock()
        self.discord_service.client.send = AsyncMock()
        
        # Test sending message
        self.discord_service.send_message("general", "Test message")
        
        # Verify
        self.discord_service.client.send.assert_called_once()
        call_args = self.discord_service.client.send.call_args[1]
        self.assertEqual(call_args["content"], "Test message")
    
    def test_send_embed(self):
        """Test embed sending."""
        # Mock Discord client
        self.discord_service.client = AsyncMock()
        self.discord_service.client.send = AsyncMock()
        
        # Test sending embed
        embed = {
            "title": "Test Embed",
            "description": "Test Description"
        }
        self.discord_service.send_embed("general", embed)
        
        # Verify
        self.discord_service.client.send.assert_called_once()
        call_args = self.discord_service.client.send.call_args[1]
        self.assertIn("embed", call_args)
        self.assertEqual(call_args["embed"]["title"], "Test Embed")
    
    def test_send_file(self):
        """Test file sending."""
        # Create test file
        test_file_path = os.path.join(self.test_config_dir, "test.txt")
        with open(test_file_path, 'w') as f:
            f.write("Test file content")
        
        # Mock Discord client
        self.discord_service.client = AsyncMock()
        self.discord_service.client.send = AsyncMock()
        
        # Test sending file
        self.discord_service.send_file("general", test_file_path)
        
        # Verify
        self.discord_service.client.send.assert_called_once()
        call_args = self.discord_service.client.send.call_args[1]
        self.assertIn("file", call_args)
    
    def test_create_channel(self):
        """Test channel creation."""
        # Mock Discord client
        self.discord_service.client = AsyncMock()
        self.discord_service.client.create_channel = AsyncMock(return_value={"id": "new_channel_id"})
        
        # Test creating channel
        channel = self.discord_service.create_channel("test_channel", "text")
        
        # Verify
        self.assertEqual(channel, "new_channel_id")
        self.discord_service.client.create_channel.assert_called_once()
    
    def test_delete_channel(self):
        """Test channel deletion."""
        # Mock Discord client
        self.discord_service.client = AsyncMock()
        self.discord_service.client.delete_channel = AsyncMock()
        
        # Test deleting channel
        self.discord_service.delete_channel("test_channel_id")
        
        # Verify
        self.discord_service.client.delete_channel.assert_called_once_with("test_channel_id")
    
    def test_get_channel_history(self):
        """Test channel history retrieval."""
        # Mock Discord client
        self.discord_service.client = AsyncMock()
        self.discord_service.client.get_channel_history = AsyncMock(return_value=[
            {"content": "Message 1"},
            {"content": "Message 2"}
        ])
        
        # Test getting history
        history = self.discord_service.get_channel_history("general", limit=2)
        
        # Verify
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["content"], "Message 1")
        self.assertEqual(history[1]["content"], "Message 2")
    
    def test_add_reaction(self):
        """Test reaction adding."""
        # Mock Discord client
        self.discord_service.client = AsyncMock()
        self.discord_service.client.add_reaction = AsyncMock()
        
        # Test adding reaction
        self.discord_service.add_reaction("test_channel_id", "test_message_id", "👍")
        
        # Verify
        self.discord_service.client.add_reaction.assert_called_once()
        call_args = self.discord_service.client.add_reaction.call_args[1]
        self.assertEqual(call_args["emoji"], "👍")
    
    def test_handle_error(self):
        """Test error handling."""
        # Test handling Discord error
        error = Exception("Discord API Error")
        self.discord_service.handle_error(error)
        
        # Verify error was logged
        self.assertTrue(self.discord_service.logger.error.called)
    
    def tearDown(self):
        """Clean up after each test."""
        # Remove test config directory
        if os.path.exists(self.test_config_dir):
            for file in os.listdir(self.test_config_dir):
                os.remove(os.path.join(self.test_config_dir, file))
            os.rmdir(self.test_config_dir)

if __name__ == '__main__':
    unittest.main() 