# test_cursor_session_manager.py

import unittest
from unittest.mock import MagicMock, patch
from selenium.webdriver.common.by import By
from cursor_session_manager import CursorSessionManager
import time

# A dummy element class to simulate Selenium WebElement behavior.
class DummyElement:
    def __init__(self, text=""):
        self.text = text

    def clear(self):
        pass

    def send_keys(self, value):
        pass

class TestCursorSessionManager(unittest.TestCase):
    def setUp(self):
        # Create a dummy config and memory_manager
        self.config = {"execution_mode": "full_sync"}
        self.memory_manager = MagicMock()

        # Create a dummy driver to simulate Selenium WebDriver.
        self.dummy_driver = MagicMock()
        # Simulate finding the prompt input element.
        dummy_prompt_input = DummyElement()
        self.dummy_driver.find_element.return_value = dummy_prompt_input
        # Simulate finding generated code elements.
        self.dummy_driver.find_elements.return_value = [
            DummyElement("Generated Code Line 1"),
            DummyElement("Generated Code Line 2")
        ]

        # Patch webdriver.Chrome to return our dummy driver.
        patcher_driver = patch('cursor_session_manager.webdriver.Chrome', return_value=self.dummy_driver)
        self.addCleanup(patcher_driver.stop)
        self.mock_chrome = patcher_driver.start()

        # Patch time.sleep to skip actual delays.
        patcher_sleep = patch('cursor_session_manager.time.sleep', return_value=None)
        self.addCleanup(patcher_sleep.stop)
        self.mock_sleep = patcher_sleep.start()

        # Initialize the CursorSessionManager instance.
        self.csm = CursorSessionManager(self.config, self.memory_manager)

    def test_switch_mode_valid(self):
        self.csm.switch_mode("tdd")
        self.assertEqual(self.csm.execution_mode, "tdd")

    def test_switch_mode_invalid(self):
        with patch('builtins.print') as mocked_print:
            self.csm.switch_mode("invalid_mode")
            mocked_print.assert_called_with("[CursorSessionManager] Invalid mode.")
            # Execution mode remains unchanged if an invalid mode is provided.
            self.assertEqual(self.csm.execution_mode, self.config["execution_mode"])

    def test_generate_prompt_full_sync(self):
        task = "Implement feature X"
        ltm_context = ["Context line 1", "Context line 2"]
        scraper_insights = [{"summary": "Insight 1", "code": "print('Hello World')"}]
        self.csm.execution_mode = "full_sync"
        prompt = self.csm.generate_prompt(task, ltm_context, scraper_insights)

        self.assertIn("# TASK: Implement feature X", prompt)
        self.assertIn("Context line 1", prompt)
        self.assertIn("Insight 1", prompt)
        self.assertIn("- Prioritize rapid development", prompt)

    def test_generate_prompt_tdd(self):
        task = "Fix bug Y"
        ltm_context = []
        scraper_insights = []
        self.csm.execution_mode = "tdd"
        prompt = self.csm.generate_prompt(task, ltm_context, scraper_insights)

        self.assertIn("# TASK: Fix bug Y", prompt)
        self.assertIn("- Follow Red-Green-Refactor cycle", prompt)

    def test_execute_prompt_success(self):
        # Execute the prompt and capture generated code.
        prompt = "Sample prompt"
        generated_code = self.csm.execute_prompt(prompt)
        expected_code = "Generated Code Line 1\nGenerated Code Line 2"
        self.assertEqual(generated_code, expected_code)

        # Verify that the prompt input element was located correctly.
        self.dummy_driver.find_element.assert_called_with(By.CSS_SELECTOR, "textarea.ai-input")
        # Verify that clear() was called on the prompt input element.
        prompt_input = self.dummy_driver.find_element.return_value
        prompt_input.clear.assert_called()

    def test_execute_prompt_failure(self):
        # Simulate failure when locating the prompt input element.
        self.dummy_driver.find_element.side_effect = Exception("Element not found")
        result = self.csm.execute_prompt("Sample prompt")
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()