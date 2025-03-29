from core.chatgpt_automation.automation_engine import AutomationEngine
import logging

class AutomationController:
    def __init__(self, helpers):
        self.helpers = helpers
        self.automation_engine = AutomationEngine()
        self.logger = logging.getLogger(__name__)

    def update_file(self, file_path, file_content):
        prompt_text = "Update this file and return the complete updated version."
        combined_prompt = f"{prompt_text}\n\n---\n\n{file_content}"
        
        try:
            response = self.automation_engine.get_chatgpt_response(combined_prompt)
            if not response:
                return "❌ No response from ChatGPT."

            updated_path = f"{file_path}.updated.py"
            if self.helpers.save_file(updated_path, response):
                return f"✅ File updated and saved: {updated_path}"
            return f"❌ Failed to save the updated file: {updated_path}"

        except Exception as e:
            self.logger.exception("Error during file update:")
            return f"❌ Error during update: {str(e)}"

    def heal_file(self, file_path):
        try:
            response = self.automation_engine.self_heal_file(file_path)
            if not response:
                return "❌ Self-heal did not produce a response."

            healed_path = f"{file_path}.selfhealed.py"
            if self.helpers.save_file(healed_path, response):
                return f"✅ File self-healed and saved: {healed_path}"
            return f"❌ Failed to save the self-healed file: {healed_path}"

        except Exception as e:
            self.logger.exception("Error during self-healing:")
            return f"❌ Error during self-heal: {str(e)}"

    def run_tests(self, file_path):
        try:
            results = self.automation_engine.run_tests(file_path)
            return f"🧪 Test results for {file_path}:\n{results}"
        except Exception as e:
            self.logger.exception("Error during test execution:")
            return f"❌ Error running tests: {str(e)}"

    def shutdown(self):
        try:
            self.automation_engine.shutdown()
            self.logger.info("Automation engine shutdown successfully.")
        except Exception as e:
            self.logger.exception("Error during shutdown:")
