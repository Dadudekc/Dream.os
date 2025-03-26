import os
import time
import json
import pickle
import logging
import shutil

# Import automation controllers (replace None with actual dependencies when available)
from core.chatgpt_automation.controllers.automation_controller import AutomationController
from core.chatgpt_automation.controllers.cursor_dispatcher import CursorDispatcher
# You can import additional modules such as a Git handler or Discord manager as needed

logger = logging.getLogger(__name__)

# Initialize controller instances
automation_controller = AutomationController(helpers=None)  # Inject actual helpers as required
cursor_dispatcher = CursorDispatcher()

def dispatch_action(intent):
    """
    Dispatches parsed intent to the appropriate system based on the action.

    Expected intent format:
      {
        "type": "command",
        "action": "run_tests",
        "args": [...],
        "payload": <parsed text>,
        "raw": <original>
      }
    """
    action = intent.get("action")
    args = intent.get("args", [])
    raw = intent.get("raw", "")

    logger.info(f"Dispatching action: {action} | Args: {args} | Raw: {raw}")

    if not action:
        logger.warning("Intent does not contain a valid action.")
        return

    try:
        if action == "run_tests":
            logger.info("🧪 Running full test suite...")
            result = automation_controller.run_tests_on_file("all")  # Adjust target as needed
            logger.info(f"Test suite result: {result}")

        elif action == "generate_tests":
            file_target = args[0] if args else None
            if not file_target:
                logger.warning("No file provided for test generation.")
                return
            logger.info(f"🧠 Generating unit tests for: {file_target}")
            cursor_dispatcher.generate_tests(file_target)

        elif action == "commit_changes":
            logger.info("📦 Committing changes via Git...")
            # Replace with actual Git interface logic here
            result = "[Simulated] Git commit complete."
            logger.info(result)

        elif action == "self_heal_file":
            file_target = args[0] if args else None
            if not file_target:
                logger.warning("No file provided for self-heal.")
                return
            result = automation_controller.self_heal_file(file_target, "")
            logger.info(f"Self-heal result: {result}")

        elif action == "retry_last_test":
            logger.info("🔁 Retrying last test...")
            # Hook into test retry mechanism here
            result = "[Simulated] Retried test run."
            logger.info(result)

        elif action == "explain_error":
            error_text = args[0] if args else "<no error>"
            logger.info(f"🔍 Explaining error: {error_text}")
            # Future integration: send error_text to an AI model for explanation
            result = f"[Simulated] Explanation for: {error_text}"
            logger.info(result)

        elif action == "generate_mock_data":
            file_target = args[0] if args else None
            logger.info(f"🧪 Generating mock data for: {file_target}")
            # Integrate your mock data builder here
            result = "[Simulated] Mock data created."
            logger.info(result)

        elif action == "share_to_discord":
            logger.info("📤 Sharing current content to Discord...")
            # Connect to DiscordManager and send message here
            result = "[Simulated] Sent to Discord."
            logger.info(result)

        elif action == "set_input_mode_voice":
            logger.info("🎙 Switching Assistant Mode to voice input...")
            # Add logic to switch mode via controller reference

        elif action == "set_input_mode_log":
            logger.info("📜 Switching Assistant Mode to log scrape input...")
            # Add logic to switch mode via controller reference

        elif action == "toggle_assistant_mode":
            logger.info("🎚 Toggling Assistant Mode...")
            # Call assistant_mode_controller.start() or .stop() as applicable

        else:
            logger.warning(f"⚠️ Unknown action: {action}")
    
    except Exception as e:
        logger.error(f"Error while executing action '{action}': {str(e)}")

if __name__ == "__main__":
    # Example intent for testing
    test_intent = {
        "type": "command",
        "action": "run_tests",
        "args": [],
        "payload": "Run tests on all modules",
        "raw": "run_tests"
    }
    dispatch_action(test_intent)
