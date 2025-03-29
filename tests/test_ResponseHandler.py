import unittest
from unittest.mock import MagicMock
import os
import sys
# Ensure the core directory is in the path if needed
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
from core.ResponseHandler import ResponseHandler

class TestResponseHandler(unittest.TestCase):
    """
    Unit tests for ResponseHandler class.
    """

    def setUp(self):
        # Mock WebDriver and the find_elements method
        self.mock_driver = MagicMock()

    def test_fetch_response_returns_latest_text(self):
        """
        Test that fetch_response returns the last message text.
        """
        mock_element = MagicMock()
        mock_element.text = "Test response"
        self.mock_driver.find_elements.return_value = [mock_element]

        handler = ResponseHandler(driver=self.mock_driver)
        response = handler.fetch_response()

        self.assertEqual(response, "Test response")

    def test_fetch_response_returns_empty_on_exception(self):
        """
        Test that fetch_response returns empty string on exception.
        """
        self.mock_driver.find_elements.side_effect = Exception("Test error")

        handler = ResponseHandler(driver=self.mock_driver)
        response = handler.fetch_response()

        self.assertEqual(response, "")

    def test_clean_response_trims_whitespace(self):
        """
        Test that clean_response trims leading and trailing whitespace.
        """
        dirty_response = "   This is a test.   "
        clean = ResponseHandler.clean_response(dirty_response)
        self.assertEqual(clean, "This is a test.")

    def test_wait_for_stable_response_returns_stable_text(self):
        """
        Test wait_for_stable_response returns when stable.
        """
        # Set up responses over time
        responses = [
            "Partial response...",
            "Partial response... more text",
            "Final complete response."
        ]

        def side_effect(*args, **kwargs):
            return [MagicMock(text=responses.pop(0))] if responses else [MagicMock(text="Final complete response.")]

        self.mock_driver.find_elements.side_effect = side_effect

        handler = ResponseHandler(driver=self.mock_driver, timeout=15, stable_period=1, poll_interval=0.1)
        final_response = handler.wait_for_stable_response()

        self.assertEqual(final_response, "Final complete response.")

if __name__ == "__main__":
    unittest.main()
