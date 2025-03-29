import os
import sys
import unittest
from unittest.mock import MagicMock, patch
# Ensure core directory is in the path if needed
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

from core.ChatManager import ChatManager
from core.DriverManager import DriverManager

class TestChatManager(unittest.TestCase):
    """
    Unit tests for the ChatManager class.
    """

    @patch("core.ChatManager.WebDriverWait")
    def test_is_logged_in_true(self, mock_wait):
        """
        Should return True when sidebar is found.
        """
        driver = MagicMock()
        driver_manager = MagicMock(spec=DriverManager)
        driver_manager.get_driver.return_value = driver
        chat_manager = ChatManager(driver_manager=driver_manager)
        mock_wait.return_value.until.return_value = True

        result = chat_manager.is_logged_in("https://chat.openai.com/")
        self.assertTrue(result)

    @patch("core.ChatManager.WebDriverWait", side_effect=Exception("Sidebar not found"))
    def test_is_logged_in_false(self, mock_wait):
        """
        Should return False when sidebar is not found.
        """
        driver = MagicMock()
        driver_manager = MagicMock(spec=DriverManager)
        driver_manager.get_driver.return_value = driver
        chat_manager = ChatManager(driver_manager=driver_manager)

        result = chat_manager.is_logged_in("https://chat.openai.com/")
        self.assertFalse(result)

    def test_ensure_model_in_url_appends_correctly(self):
        """
        Should append model param if missing.
        """
        driver_manager = MagicMock(spec=DriverManager)
        chat_manager = ChatManager(driver_manager=driver_manager)

        base_url = "https://chat.openai.com/c/abc123"
        expected = "https://chat.openai.com/c/abc123?model=gpt-4o-mini"

        result = chat_manager.ensure_model_in_url(base_url)
        self.assertEqual(result, expected)

    def test_ensure_model_in_url_with_existing_params(self):
        """
        Should append model param with & separator if other params exist.
        """
        driver_manager = MagicMock(spec=DriverManager)
        chat_manager = ChatManager(driver_manager=driver_manager)

        base_url = "https://chat.openai.com/c/abc123?existing=param"
        expected = "https://chat.openai.com/c/abc123?existing=param&model=gpt-4o-mini"

        result = chat_manager.ensure_model_in_url(base_url)
        self.assertEqual(result, expected)

    def test_ensure_model_in_url_with_model_already_present(self):
        """
        Should not modify URL if model param already present.
        """
        driver_manager = MagicMock(spec=DriverManager)
        chat_manager = ChatManager(driver_manager=driver_manager)

        base_url = "https://chat.openai.com/c/abc123?model=gpt-4o-mini"
        expected = base_url

        result = chat_manager.ensure_model_in_url(base_url)
        self.assertEqual(result, expected)

    @patch("core.ChatManager.time.sleep", return_value=None)
    @patch("core.ChatManager.WebDriverWait")
    def test_get_all_chat_titles_scrolls_and_filters(self, mock_wait, mock_sleep):
        """
        Should scroll, gather all chat links, and exclude specified chats.
        """
        driver = MagicMock()
        driver_manager = MagicMock(spec=DriverManager)
        driver_manager.get_driver.return_value = driver

        # Simulate sidebar element for scrolling
        mock_sidebar = MagicMock()
        mock_wait.return_value.until.return_value = mock_sidebar

        # Simulate chats that will load in two scroll iterations
        chats_iteration_1 = [
            self.create_mock_chat("Chat 1", "https://chat.openai.com/c/abc111"),
            self.create_mock_chat("Excluded Chat", "https://chat.openai.com/c/abc222")
        ]
        chats_iteration_2 = chats_iteration_1 + [
            self.create_mock_chat("Chat 2", "https://chat.openai.com/c/abc333")
        ]

        # Set find_elements return values for 2 iterations + 1 extra where nothing new is found
        driver.find_elements.side_effect = [
            chats_iteration_1,  # First loop
            chats_iteration_2,  # Second loop (new chat added)
            chats_iteration_2   # Third loop (no change, exit)
        ]

        chat_manager = ChatManager(driver_manager=driver_manager, excluded_chats=["Excluded Chat"], scroll_pause=0)

        results = chat_manager.get_all_chat_titles("https://chat.openai.com/")

        self.assertEqual(len(results), 2)
        titles = [r['title'] for r in results]

        self.assertIn("Chat 1", titles)
        self.assertIn("Chat 2", titles)

    def create_mock_chat(self, title, href):
        """
        Helper for mocking chat elements.
        """
        mock_chat = MagicMock()
        mock_chat.text.strip.return_value = title
        mock_chat.get_attribute.return_value = href
        return mock_chat


if __name__ == "__main__":
    unittest.main()
