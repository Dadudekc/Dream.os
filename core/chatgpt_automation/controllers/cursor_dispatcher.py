import logging
import subprocess
import os
from core.PathManager import PathManager  # Updated import

logger = logging.getLogger(__name__)

class CursorDispatcher:
    def __init__(self):
        self.project_root = PathManager.get_path('base')  # Use PathManager
        self.prompts_dir = os.path.join(self.project_root, "cursor_prompts")
        self.output_dir = os.path.join(self.project_root, "cursor_output")

    def generate_tests(self, file_path):
        """
        Trigger test generation for a given Python file using Cursor.
        """
        logger.info(f"🧪 Dispatching to Cursor: generate tests for {file_path}")
        prompt_file = os.path.join(self.prompts_dir, "generate_tests.prompt.md")
        try:
            subprocess.run([
                "cursor",
                "prompt",
                file_path,
                "--template", prompt_file
            ], check=True)
            logger.info(f"✅ Test generation completed for: {file_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Cursor test generation failed: {e}")

    def self_heal(self, file_path):
        """
        Attempt to self-heal the file via a Cursor prompt.
        """
        logger.info(f"🩹 Self-healing file: {file_path}")
        prompt_file = os.path.join(self.prompts_dir, "self_heal.prompt.md")
        try:
            subprocess.run([
                "cursor",
                "prompt",
                file_path,
                "--template", prompt_file
            ], check=True)
            logger.info(f"✅ Self-heal attempt complete for: {file_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Cursor self-heal failed: {e}")

    def run_feedback_loop(self, file_path, error_text):
        """
        Send an error trace + the source file to Cursor and request a fix.
        """
        logger.info(f"♻️ Running feedback loop on {file_path} with error: {error_text}")
        prompt_file = os.path.join(self.prompts_dir, "feedback_loop.prompt.md")
        try:
            with open("error_log.txt", "w", encoding="utf-8") as f:
                f.write(error_text)
            subprocess.run([
                "cursor",
                "prompt",
                file_path,
                "--template", prompt_file,
                "--input", "error_log.txt"
            ], check=True)
            logger.info("✅ Feedback loop prompt sent to Cursor.")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Feedback loop failed: {e}")
