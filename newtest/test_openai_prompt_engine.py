# test_openai_prompt_engine.py

import os
import json
import shutil
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from openai_prompt_engine import OpenAIPromptEngine
from config import INTERACTION_LOG_PATH, RETRY_ATTEMPTS

# Create a dummy Selenium element that returns specified text.
class DummyElement:
    def __init__(self, text):
        self.text = text

    def clear(self):
        pass

    def send_keys(self, value):
        pass

# Dummy WebDriverWait function that immediately returns a dummy element.
def dummy_wait(driver, timeout, condition):
    # If the condition is for the prompt input, return a DummyElement.
    return DummyElement("")

class OpenAIPromptEngineTest(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for Jinja2 templates.
        self.temp_dir = tempfile.mkdtemp()
        self.template_name = "test_template.j2"
        self.template_path = os.path.join(self.temp_dir, self.template_name)
        
        # Write a simple Jinja2 template.
        with open(self.template_path, "w") as f:
            f.write("Prompt: {{ CURRENT_MEMORY_STATE }}; {{ ADDITIONAL_CONTEXT }}")
        
        # Create a dummy Selenium driver with necessary methods.
        self.driver = MagicMock()
        # Simulate driver.title for health check.
        self.driver.title = "Dummy Title"
        # Simulate get method.
        self.driver.get = MagicMock()
        # Simulate find_elements for the response container.
        self.dummy_response_text = "This is a test response."
        self.driver.find_elements.return_value = [DummyElement("First message"), DummyElement(self.dummy_response_text)]
        
        # Patch WebDriverWait.until to use our dummy_wait function.
        patcher = patch("openai_prompt_engine.WebDriverWait.until", side_effect=lambda cond: dummy_wait(self.driver, 15, cond))
        self.addCleanup(patcher.stop)
        self.mock_wait = patcher.start()
        
        # Initialize our prompt engine with the temporary template directory.
        self.engine = OpenAIPromptEngine(driver=self.driver, template_dir=self.temp_dir)

        # Ensure the interaction log file is removed before tests.
        if os.path.exists(INTERACTION_LOG_PATH):
            os.remove(INTERACTION_LOG_PATH)

    def tearDown(self):
        # Remove the temporary directory and its contents.
        shutil.rmtree(self.temp_dir)
        # Cleanup the interaction log file if it was created.
        if os.path.exists(INTERACTION_LOG_PATH):
            os.remove(INTERACTION_LOG_PATH)

    def test_render_prompt(self):
        memory_state = {"test_key": "test_value"}
        additional_context = "Extra context"
        rendered = self.engine.render_prompt(self.template_name, memory_state, additional_context)
        self.assertIn("test_value", rendered)
        self.assertIn("Extra context", rendered)
    
    def test_driver_health_check(self):
        # Driver is healthy by default.
        self.assertTrue(self.engine._is_driver_alive())
        # Simulate an exception on driver.title.
        self.driver.title = None
        self.driver.title.side_effect = Exception("Driver error")
        self.assertFalse(self.engine._is_driver_alive())
    
    def test_send_prompt_and_scrape_response(self):
        # Test that send_prompt calls driver.get and scrapes response correctly.
        prompt = "Test prompt"
        response = self.engine.send_prompt(prompt)
        self.driver.get.assert_called_with(self.engine.driver.get.call_args[0][0])
        self.assertEqual(response, self.dummy_response_text)

    def test_retry_backoff_logic(self):
        # Simulate a function that fails a couple of times before succeeding.
        call_count = {"count": 0}

        def flaky_function():
            if call_count["count"] < 2:
                call_count["count"] += 1
                raise Exception("Transient error")
            return "Success"

        result = self.engine._retry(flaky_function)
        self.assertEqual(result, "Success")
        # Ensure the function was attempted at least 3 times in worst case.
        self.assertEqual(call_count["count"], 2)
    
    def test_log_interaction(self):
        prompt = "Test prompt for logging"
        response = "Test response for logging"
        metadata = {"source": "unittest"}
        self.engine.log_interaction(prompt, response, metadata)
        
        # Verify that the log file exists and contains the logged interaction.
        self.assertTrue(os.path.exists(INTERACTION_LOG_PATH))
        with open(INTERACTION_LOG_PATH, "r") as f:
            data = json.load(f)
            self.assertTrue(isinstance(data, list))
            self.assertEqual(len(data), 1)
            log_entry = data[0]
            self.assertEqual(log_entry["prompt"], prompt)
            self.assertEqual(log_entry["response"], response)
            self.assertEqual(log_entry["metadata"], metadata)
            # Check if timestamp exists and is in ISO format.
            try:
                datetime.fromisoformat(log_entry["timestamp"])
            except ValueError:
                self.fail("Timestamp is not in ISO format.")

if __name__ == "__main__":
    unittest.main()