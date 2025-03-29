import unittest
from unittest.mock import MagicMock, patch
from core.ChatManager import ChatManager, sanitize_filename

# Dummy configs for testing
DUMMY_CONFIG = {
    "CHATGPT_URL": "https://chat.openai.com/"
}

class TestChatManager(unittest.TestCase):
    def setUp(self):
        # Patch external modules and classes
        self.patcher_driver_manager = patch('core.ChatManager.UnifiedDriverManager')
        self.mock_driver_manager = self.patcher_driver_manager.start()

        self.patcher_prompt_engine = patch('core.ChatManager.PromptEngine')
        self.mock_prompt_engine = self.patcher_prompt_engine.start()

        self.patcher_discord_manager = patch('core.ChatManager.DiscordManager')
        self.mock_discord_manager = self.patcher_discord_manager.start()

        self.patcher_prompt_manager = patch('core.ChatManager.AletheiaPromptManager')
        self.mock_prompt_manager = self.patcher_prompt_manager.start()

        self.patcher_config = patch('core.ChatManager.Config', DUMMY_CONFIG)
        self.patcher_config.start()

        # Mocks
        self.mock_driver = MagicMock()
        self.mock_driver_manager.return_value.get_driver.return_value = self.mock_driver
        self.mock_prompt_engine.return_value = MagicMock()

        # Create the ChatManager instance
        self.chat_manager = ChatManager(headless=True)

    def tearDown(self):
        self.patcher_driver_manager.stop()
        self.patcher_prompt_engine.stop()
        self.patcher_discord_manager.stop()
        self.patcher_prompt_manager.stop()
        self.patcher_config.stop()

    def test_invalid_model_raises_value_error(self):
        with self.assertRaises(ValueError):
            ChatManager(model="invalid-model")

    def test_set_model_valid(self):
        self.chat_manager.set_model("gpt-4o")
        self.assertEqual(self.chat_manager.model, "gpt-4o")

    def test_set_model_invalid(self):
        with self.assertRaises(ValueError):
            self.chat_manager.set_model("invalid_model")

    def test_ensure_model_in_url_adds_model(self):
        url = "https://chat.openai.com/chat"
        updated_url = self.chat_manager.ensure_model_in_url(url)
        self.assertIn(f"model={self.chat_manager.model}", updated_url)

    def test_is_logged_in_success(self):
        self.mock_driver.get.return_value = None
        self.mock_driver.find_element.return_value = MagicMock()
        with patch('selenium.webdriver.support.ui.WebDriverWait.until', return_value=True):
            result = self.chat_manager.is_logged_in()
        self.assertTrue(result)

    def test_is_logged_in_failure(self):
        self.mock_driver.get.return_value = None
        with patch('selenium.webdriver.support.ui.WebDriverWait.until', side_effect=Exception("No element")):
            result = self.chat_manager.is_logged_in()
        self.assertFalse(result)

    def test_get_all_chat_titles_no_chats(self):
        self.mock_driver.get.return_value = None
        self.mock_driver.find_elements.return_value = []
        with patch('selenium.webdriver.support.ui.WebDriverWait.until', return_value=True):
            chats = self.chat_manager.get_all_chat_titles()
        self.assertEqual(chats, [])

    def test_execute_prompts_single_chat_login_required(self):
        self.chat_manager.is_logged_in = MagicMock(return_value=False)
        results = self.chat_manager.execute_prompts_single_chat(prompts=["Test Prompt"])
        self.assertEqual(results, [])

    def test_execute_prompts_single_chat_success(self):
        self.chat_manager.is_logged_in = MagicMock(return_value=True)
        self.chat_manager.prompt_engine.send_prompt.return_value = True
        self.chat_manager.prompt_engine.wait_for_stable_response.return_value = "Test response"

        results = self.chat_manager.execute_prompts_single_chat(prompts=["Prompt A"])
        self.assertEqual(results, ["Test response"])

    def test_execute_prompt_cycle_login_required(self):
        self.chat_manager.is_logged_in = MagicMock(return_value=False)
        result = self.chat_manager.execute_prompt_cycle("Test Prompt")
        self.assertEqual(result, "")

    def test_execute_prompt_cycle_success(self):
        self.chat_manager.is_logged_in = MagicMock(return_value=True)
        self.chat_manager.prompt_engine.send_prompt.return_value = True
        self.chat_manager.prompt_engine.wait_for_stable_response.return_value = "Cycle Response"

        result = self.chat_manager.execute_prompt_cycle("Test Prompt")
        self.assertEqual(result, "Cycle Response")

    def test_execute_prompt_to_chat_no_link(self):
        self.chat_manager.is_logged_in = MagicMock(return_value=True)
        chat_info = {"title": "Test Chat", "link": None}
        result = self.chat_manager.execute_prompt_to_chat("Test Prompt", chat_info)
        self.assertEqual(result, "")

    def test_execute_prompt_to_chat_success(self):
        self.chat_manager.is_logged_in = MagicMock(return_value=True)
        self.chat_manager.prompt_engine.send_prompt.return_value = True
        self.chat_manager.prompt_engine.wait_for_stable_response.return_value = "Prompt Response"

        chat_info = {"title": "Chat", "link": "https://chat.openai.com/chat"}
        result = self.chat_manager.execute_prompt_to_chat("Test Prompt", chat_info)
        self.assertEqual(result, "Prompt Response")

    def test_execute_prompts_on_all_chats(self):
        self.chat_manager.is_logged_in = MagicMock(return_value=True)
        self.chat_manager.prompt_engine.send_prompt.return_value = True
        self.chat_manager.prompt_engine.wait_for_stable_response.return_value = "Chat Response"

        chat_list = [
            {"title": "Chat 1", "link": "https://chat.openai.com/chat1"},
            {"title": "Chat 2", "link": "https://chat.openai.com/chat2"}
        ]

        results = self.chat_manager.execute_prompts_on_all_chats(["Prompt A"], chat_list)
        self.assertIn("Chat 1", results)
        self.assertIn("Chat 2", results)

    def test_cycle_prompts_through_all_chats(self):
        self.chat_manager.is_logged_in = MagicMock(return_value=True)
        self.chat_manager.get_all_chat_titles = MagicMock(return_value=[
            {"title": "Chat A", "link": "https://chat.openai.com/chatA"}
        ])
        self.chat_manager.prompt_engine.send_prompt.return_value = True
        self.chat_manager.prompt_engine.wait_for_stable_response.return_value = "Response A"

        with patch('os.makedirs'), patch('builtins.open', unittest.mock.mock_open()):
            self.chat_manager.cycle_prompts_through_all_chats(["Prompt A"])

    def test_generate_dreamscape_episodes(self):
        self.chat_manager.is_logged_in = MagicMock(return_value=True)
        self.chat_manager.get_all_chat_titles = MagicMock(return_value=[
            {"title": "Chat A", "link": "https://chat.openai.com/chatA"}
        ])
        self.chat_manager.prompt_manager.get_prompt.return_value = "Dreamscape Prompt"
        self.chat_manager.prompt_engine.send_prompt.return_value = True
        self.chat_manager.prompt_engine.wait_for_stable_response.return_value = "Episode Response"

        with patch('os.makedirs'), patch('builtins.open', unittest.mock.mock_open()):
            self.chat_manager.generate_dreamscape_episodes()

    def test_analyze_execution_response(self):
        response = self.chat_manager.analyze_execution_response("Sample response", "Sample prompt")
        self.assertIn("victor_tactics_used", response)

    def test_sanitize_filename(self):
        unsafe_filename = "Test/Unsafe:Filename?*"
        safe_filename = sanitize_filename(unsafe_filename)
        self.assertNotIn("/", safe_filename)
        self.assertNotIn(":", safe_filename)

if __name__ == '__main__':
    unittest.main()