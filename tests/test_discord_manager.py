import unittest
from unittest.mock import patch, MagicMock, mock_open
import asyncio
import os
import json

from core.services.discord.DiscordManager import DiscordManager, DiscordSettingsDialog

# Dummy data
DUMMY_TOKEN = "dummy_token"
DUMMY_CHANNEL_ID = 1234567890
DUMMY_CONFIG_FILE = "discord_manager_config.json"

class TestDiscordManager(unittest.TestCase):
    def setUp(self):
        # Patch Discord client to avoid actual network calls
        patcher_bot = patch('core.DiscordManager.commands.Bot')
        self.mock_bot = patcher_bot.start()
        self.addCleanup(patcher_bot.stop)

        # Patch EventMessageBuilder
        patcher_event_builder = patch('core.DiscordManager.EventMessageBuilder')
        self.mock_event_builder = patcher_event_builder.start()
        self.addCleanup(patcher_event_builder.stop)

        # Patch logger
        patcher_logger = patch('core.DiscordManager.logger')
        self.mock_logger = patcher_logger.start()
        self.addCleanup(patcher_logger.stop)

        # Instantiate DiscordManager with dummy token/channel
        self.manager = DiscordManager(bot_token=DUMMY_TOKEN, channel_id=DUMMY_CHANNEL_ID)

        # Override config path for test isolation
        self.manager.CONFIG_FILE = DUMMY_CONFIG_FILE

    def tearDown(self):
        if os.path.exists(DUMMY_CONFIG_FILE):
            os.remove(DUMMY_CONFIG_FILE)

    # ---------- CONFIG TESTS ----------
    def test_load_config_file_not_exists(self):
        self.manager.load_config()
        # Should not raise exceptions and fallback to defaults
        self.assertEqual(self.manager.bot_token, DUMMY_TOKEN)

    def test_save_and_load_config_success(self):
        self.manager.update_credentials("new_token", 987654321)
        self.manager.save_config()

        # Confirm file written
        self.assertTrue(os.path.exists(DUMMY_CONFIG_FILE))

        # Reload config
        self.manager.bot_token = ""
        self.manager.default_channel_id = 0
        self.manager.load_config()

        self.assertEqual(self.manager.bot_token, "new_token")
        self.assertEqual(self.manager.default_channel_id, 987654321)

    def test_update_credentials(self):
        self.manager.update_credentials("new_bot_token", 111111)
        self.assertEqual(self.manager.bot_token, "new_bot_token")
        self.assertEqual(self.manager.default_channel_id, 111111)

    # ---------- PROMPT-CHANNEL MAPPING ----------
    def test_map_prompt_to_channel(self):
        self.manager.map_prompt_to_channel("test_prompt", 222222)
        self.assertEqual(self.manager.prompt_channel_map["test_prompt"], 222222)

    def test_unmap_prompt_channel(self):
        self.manager.prompt_channel_map = {"test_prompt": 222222}
        self.manager.unmap_prompt_channel("test_prompt")
        self.assertNotIn("test_prompt", self.manager.prompt_channel_map)

    def test_get_channel_for_prompt(self):
        self.manager.prompt_channel_map = {"test_prompt": 222222}
        self.assertEqual(self.manager.get_channel_for_prompt("test_prompt"), 222222)
        self.assertEqual(self.manager.get_channel_for_prompt("unknown_prompt"), DUMMY_CHANNEL_ID)

    # ---------- BOT CONTROL ----------
    @patch('core.DiscordManager.QMessageBox')
    def test_run_bot_without_credentials(self, mock_qmessagebox):
        self.manager.config["bot_token"] = ""
        self.manager.config["default_channel_id"] = 0
        self.manager.run_bot()

        mock_qmessagebox.warning.assert_called_once()

    @patch('core.DiscordManager.threading.Thread')
    def test_run_bot_with_valid_credentials(self, mock_thread):
        self.manager.config["bot_token"] = "valid_token"
        self.manager.config["default_channel_id"] = 1111

        self.manager.run_bot()

        mock_thread.assert_called_once()

    def test_stop_bot(self):
        self.manager.is_running = True
        self.manager.bot.loop = MagicMock()
        self.manager.bot.loop.is_running.return_value = True
        self.manager.bot_loop_thread = MagicMock()

        self.manager.stop_bot()

        self.assertFalse(self.manager.is_running)

    # ---------- MESSAGE SENDING ----------
    def test_send_message_when_bot_not_running(self):
        self.manager.is_running = False
        self.manager.send_message("test", "message")
        self.manager._log.assert_called_with("⚠️ Bot not running. Cannot send message.", level=30)

    def test_send_file_when_bot_not_running(self):
        self.manager.is_running = False
        self.manager.send_file("test", "file.txt")
        self.manager._log.assert_called_with("⚠️ Bot not running. Cannot send file.", level=30)

    @patch("builtins.open", new_callable=mock_open, read_data="episode text")
    def test_send_dreamscape_episode_as_message(self, mock_file):
        self.manager.is_running = True
        file_path = "episode.txt"
        with patch('os.path.exists', return_value=True):
            self.manager.send_dreamscape_episode("dreamscape", file_path, post_full_text=True)

        self.manager._log.assert_any_call("✅ Sent Dreamscape episode text for prompt 'dreamscape'")

    @patch("builtins.open", new_callable=mock_open, read_data="long text" * 1000)
    def test_send_dreamscape_episode_as_file(self, mock_file):
        self.manager.is_running = True
        file_path = "episode.txt"
        with patch('os.path.exists', return_value=True):
            self.manager.send_dreamscape_episode("dreamscape", file_path, post_full_text=True)

        self.manager._log.assert_any_call("✅ Sent Dreamscape episode file for prompt 'dreamscape'")

    def test_send_prompt_response_text(self):
        self.manager.is_running = True
        short_response = "Short response"
        self.manager.send_prompt_response("prompt", response_text=short_response)

        self.manager._log.assert_any_call("✅ Queued message for prompt 'prompt': Short response")

    @patch("builtins.open", new_callable=mock_open, read_data="long response" * 1000)
    def test_send_prompt_response_file(self, mock_file):
        self.manager.is_running = True
        response_file = "response.txt"
        with patch('os.path.exists', return_value=True):
            self.manager.send_prompt_response("prompt", response_file=response_file)

        self.manager._log.assert_any_call("✅ Queued file for prompt 'prompt': response.txt")

    def test_send_event_notification(self):
        self.manager.is_running = True
        event_data = {"quest": "Complete"}
        self.manager.send_event_notification("quest_complete", event_data)

        self.manager._log.assert_any_call("✅ Queued message for prompt 'quest_complete'")

    def test_update_status(self):
        self.manager.update_status("cycle_active", True)
        self.assertTrue(self.manager.status_data["cycle_active"])

# ------------------------------------------------------------------------
# DiscordSettingsDialog Tests
# ------------------------------------------------------------------------

@patch('core.DiscordManager.QMessageBox')
@patch('core.DiscordManager.QLineEdit')
@patch('core.DiscordManager.QListWidget')
@patch('core.DiscordManager.QComboBox')
class TestDiscordSettingsDialog(unittest.TestCase):
    def setUp(self):
        # Mock the DiscordManager dependency
        self.mock_manager = MagicMock()
        self.dialog = DiscordSettingsDialog(discord_manager=self.mock_manager)

    def test_update_credentials_success(self, mock_combo, mock_list, mock_line, mock_msgbox):
        self.dialog.bot_token_input.text.return_value = "new_token"
        self.dialog.channel_id_input.text.return_value = "123456"

        self.dialog.update_credentials()

        self.mock_manager.update_credentials.assert_called_with("new_token", 123456)
        mock_msgbox.information.assert_called()

    def test_map_prompt_to_channel_success(self, mock_combo, mock_list, mock_line, mock_msgbox):
        self.dialog.prompt_type_combo.currentText.return_value = "prompt_type"
        self.dialog.prompt_channel_input.text.return_value = "78910"

        self.dialog.map_prompt_to_channel()

        self.mock_manager.map_prompt_to_channel.assert_called_with("prompt_type", 78910)
        mock_msgbox.information.assert_called()

    def test_unmap_selected_prompt_success(self, mock_combo, mock_list, mock_line, mock_msgbox):
        # Setup selectedItems to return an item with text
        mock_item = MagicMock()
        mock_item.text.return_value = "prompt_type -> 111"
        self.dialog.prompt_channel_list.selectedItems.return_value = [mock_item]

        self.dialog.unmap_selected_prompt()

        self.mock_manager.unmap_prompt_channel.assert_called_with("prompt_type")
        mock_msgbox.information.assert_called()

    def test_refresh_prompt_channel_list_with_mappings(self, mock_combo, mock_list, mock_line, mock_msgbox):
        self.mock_manager.prompt_channel_map = {"promptA": 123, "promptB": 456}
        self.dialog.refresh_prompt_channel_list()

        self.assertEqual(self.dialog.prompt_channel_list.addItem.call_count, 2)

    def test_load_prompt_types_file_not_found(self, mock_combo, mock_list, mock_line, mock_msgbox):
        # Mock os.path.exists to return False
        with patch("os.path.exists", return_value=False):
            prompts = self.dialog.load_prompt_types()
        self.assertEqual(prompts, [])

if __name__ == '__main__':
    unittest.main()
