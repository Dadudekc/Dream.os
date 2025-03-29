import os
import subprocess
import time
from pathlib import Path
import logging
import json

from ..OpenAIClient import OpenAIClient  # Import the class instead of a function

logger = logging.getLogger(__name__)

def validate_test_code(code):
    """
    Basic validation: ensure the code is non-empty and contains a test class or test method.
    """
    if not code:
        return False
    if "unittest" not in code:
        return False
    if "class Test" not in code and "def test_" not in code:
        return False
    return True

class TestAgent:
    def __init__(self, driver, helpers, timeout=120, tracker=None):
        """
        :param driver: ChatGPT driver instance.
        :param helpers: An instance of GuiHelpers for file I/O and logging.
        :param timeout: Timeout for ChatGPT responses.
        :param tracker: Optional ModelPerformanceTracker instance for performance-based fallback.
        """
        self.driver = driver
        self.helpers = helpers
        self.timeout = timeout
        self.tracker = tracker

    def run_full_test_cycle(self, file_path):
        """
        Generate tests for the given file, run them, and if they fail, trigger a repair cycle.
        Retries up to max_attempts. If still failing and a tracker is provided,
        uses the tracker to choose the best model override for one final attempt.
        Returns (success, output).
        """
        logger.info(f"🧠 Starting self-healing test cycle for {file_path}...")
        success, output, prev_test_code = self.generate_and_run(file_path)

        attempts = 0
        max_attempts = 3

        while not success and attempts < max_attempts:
            logger.warning(f"🩹 Attempt {attempts + 1}: Repairing failed tests for {file_path}...")
            success, output, new_test_code = self.repair_tests(file_path, output, prev_test_code)
            if new_test_code == prev_test_code:
                logger.warning("⚠️ No change in test code after repair attempt. Aborting further retries.")
                break
            prev_test_code = new_test_code
            attempts += 1

        # If still failing and tracker is provided, try with best model from performance tracker.
        if not success and self.tracker is not None:
            best_model = self.tracker.choose_model(epsilon=0.0)
            logger.info(f"🔧 Fallback: Using best-performing model from tracker: {best_model}")
            success, output, _ = self.generate_and_run(file_path, override_model=best_model)

        logger.info(f"✅ Test cycle complete for {file_path}. Success: {success}")
        return success, output

    def generate_and_run(self, file_path, override_model=None):
        """
        Generate tests for a file (optionally with an override model), validate them, and run the tests.
        Returns a tuple: (success, output, generated_test_code).
        """
        test_file = self.create_tests_for_file(file_path, override_model=override_model)
        if not test_file:
            return False, "❌ Test file creation failed.", None

        test_code = self.helpers.read_file(test_file)
        if not self.validate_test_file(test_code):
            return False, "❌ Generated test file is invalid.", test_code

        success, output = self.run_tests(test_file)
        return success, output, test_code

    def create_tests_for_file(self, file_path, override_model=None):
        """
        Reads the target file, constructs a prompt to generate tests (optionally forcing a model style),
        and saves the response as a test file.
        """
        file_content = self.helpers.read_file(file_path)
        if file_content is None:
            logger.error("❌ Could not read file content.")
            return None

        if override_model:
            prompt = (
                f"Using the {override_model} style, write a complete set of unit tests for the following Python code using the unittest framework. "
                f"Cover edge cases and use mocks for external dependencies if needed. "
                f"Return only the test code.\n\n"
                f"=== CODE START ===\n{file_content}\n=== CODE END ===\n"
            )
        else:
            prompt = (
                f"Write a complete set of unit tests for the following Python code using the unittest framework. "
                f"Cover edge cases and use mocks for external dependencies if needed. "
                f"Return only the test code.\n\n"
                f"=== CODE START ===\n{file_content}\n=== CODE END ===\n"
            )

        logger.info(f"📤 Sending prompt to generate tests for {file_path}...")
        test_code = self.driver.get_chatgpt_response(prompt, timeout=self.timeout)  # Use the method from the OpenAIClient instance
        if not test_code:
            logger.error("❌ No test code received.")
            return None

        if not self.validate_test_file(test_code):
            logger.warning("⚠️ Generated test code failed validation.")
            return None

        test_file_path = self.get_test_file_path(file_path)
        if self.helpers.save_file(test_file_path, test_code):
            logger.info(f"✅ Test file saved: {test_file_path}")
            return test_file_path
        else:
            return None

    def validate_test_file(self, test_code):
        is_valid = validate_test_code(test_code)
        if not is_valid:
            logger.warning("⚠️ Generated test file did not pass validation.")
        return is_valid

    def run_tests(self, test_file):
        """
        Executes the test file using the unittest framework.
        Returns (success, output).
        """
        logger.info(f"🧪 Running tests: {test_file}")
        try:
            result = subprocess.run(
                ["python", "-m", "unittest", test_file],
                capture_output=True, text=True, timeout=300
            )
        except subprocess.TimeoutExpired as e:
            logger.error(f"❌ Timeout when running tests: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"❌ Exception when running tests: {e}")
            return False, str(e)

        output = result.stdout + "\n" + result.stderr
        success = (result.returncode == 0)
        if success:
            logger.info(f"✅ Tests PASSED for {test_file}.\n{output}")
        else:
            logger.warning(f"❌ Tests FAILED for {test_file}.\n{output}")
        return success, output

    def repair_tests(self, file_path, failure_output, previous_test_code):
        """
        Prompts ChatGPT to repair the test code based on the failure trace.
        Returns (success, output, new_test_code).
        """
        current_test_file = self.get_test_file_path(file_path)
        test_code = self.helpers.read_file(current_test_file)
        file_content = self.helpers.read_file(file_path)
        if not test_code or not file_content:
            logger.error("❌ Unable to read test code or original file for repair.")
            return False, "❌ Unable to read necessary files.", None

        prompt = (
            f"The following test code is failing with this error:\n\n"
            f"=== FAILURE TRACE ===\n{failure_output}\n\n"
            f"=== ORIGINAL FILE CODE ===\n{file_content}\n\n"
            f"=== CURRENT TEST CODE ===\n{test_code}\n\n"
            f"Please fix the test code and return only the corrected test code."
        )

        logger.info("📤 Sending prompt to repair test code...")
        fixed_test_code = self.driver.get_chatgpt_response(prompt, timeout=self.timeout)  # Use the method from the OpenAIClient instance
        if not fixed_test_code:
            logger.error("❌ Repair failed: no response from ChatGPT.")
            return False, "❌ Repair failed: no response from ChatGPT.", test_code

        if not self.helpers.save_file(current_test_file, fixed_test_code):
            logger.error("❌ Repair failed: could not save fixed test code.")
            return False, "❌ Repair failed: could not save fixed test code.", test_code

        success, output = self.run_tests(current_test_file)
        return success, output, fixed_test_code

    def get_test_file_path(self, file_path):
        """
        Determines the tests folder relative to the project root.
        If a tests folder exists (via markers), use it; otherwise, create one.
        """
        project_root = self.find_project_root(file_path)
        tests_dir = Path(project_root) / "tests"
        if not tests_dir.exists():
            logger.info(f"🔨 Creating tests directory at {tests_dir}")
            tests_dir.mkdir(parents=True, exist_ok=True)
        base_name = os.path.basename(file_path)
        name_without_ext, _ = os.path.splitext(base_name)
        test_file = tests_dir / f"test_{name_without_ext}.py"
        logger.info(f"📄 Test file path resolved: {test_file}")
        return str(test_file)

    def find_project_root(self, file_path):
        """
        Walks upward from the file's location to find the project root.
        Assumes a directory containing .git, setup.py, or pyproject.toml is the root.
        """
        path = Path(file_path).resolve().parent
        while path != path.parent:
            if any((path / marker).exists() for marker in [".git", "setup.py", "pyproject.toml"]):
                logger.info(f"🏠 Project root found: {path}")
                return path
            path = path.parent
        logger.warning(f"⚠️ No project root found. Defaulting to {path}")
        return path

# ---------------------------
# Example usage:
# ---------------------------
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    from chatgpt_automation.OpenAIClient import get_openai_driver, login_openai
    from GUI.GuiHelpers import GuiHelpers

    helpers = GuiHelpers()
    driver = get_openai_driver(profile_path=os.getcwd(), headless=False)
    if login_openai(driver):
        test_agent = TestAgent(driver, helpers)
        file_to_test = "example_module.py"  # Replace with your target file
        success, output = test_agent.run_full_test_cycle(file_to_test)
        print("Test Cycle Success:", success)
        print("Test Output:\n", output)
    driver.quit()
