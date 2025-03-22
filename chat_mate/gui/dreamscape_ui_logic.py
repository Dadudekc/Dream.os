import threading
import logging
from gui.dreamscape_services import DreamscapeService

class DreamscapeUILogic:
    """
    Bridges UI interactions with backend services.
    Provides async support and emits signals for UI updates.
    """

    def __init__(self, output_callback=None):
        """
        Initializes the UILogic with backend services and UI callback functions.
        
        :param output_callback: Callable to append logs to the UI.
        """
        self.output_callback = output_callback or print
        self.discord_log_callback = None
        self.status_update_callback = None
        self.service = None  # Will be set by the main application
        self.logger = logging.getLogger(__name__)

    # --- Signal Handlers ---

    def set_output_signal(self, output_signal_func):
        """
        Set the callback for appending standard output/log messages.
        """
        self.output_callback = output_signal_func

    def set_discord_log_signal(self, discord_log_signal_func):
        """
        Set the callback for appending Discord log messages.
        """
        self.discord_log_callback = discord_log_signal_func

    def set_status_update_signal(self, status_update_signal_func):
        """
        Set the callback for updating UI status messages.
        """
        self.status_update_callback = status_update_signal_func

    # --- Logging Helpers ---

    def _output(self, message: str):
        """Output a message to the UI and log it."""
        if callable(self.output_callback):
            self.output_callback(message)
        self.logger.info(message)

    def _discord_log(self, message: str):
        """Output a Discord-related message to the UI and log it."""
        if callable(self.discord_log_callback):
            self.discord_log_callback(message)
        self.logger.info(f"[Discord] {message}")

    def _update_status(self, message: str):
        """Update the UI status and log it."""
        if callable(self.status_update_callback):
            self.status_update_callback(message)
        self.logger.info(f"[Status] {message}")

    # --- Service Access ---

    def get_service(self, service_name: str):
        """Get a service by name, with proper error handling."""
        if not self.service:
            self._output(f"Error: Service '{service_name}' not available - services not initialized")
            return None
        return getattr(self.service, service_name, None)

    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is available."""
        return bool(self.get_service(service_name))

    # --- UI Action Handlers ---

    def execute_prompt(self, prompt_text: str):
        """Execute a prompt and handle the response."""
        if not self.is_service_available('prompt_manager'):
            self._output("Error: Prompt manager not available")
            return []

        try:
            self._update_status("Executing prompt...")
            responses = self.service.prompt_manager.execute_prompt(prompt_text)
            self._output(f"Prompt executed successfully. Got {len(responses)} responses.")
            return responses
        except Exception as e:
            self._output(f"Error executing prompt: {str(e)}")
            return []

    def save_prompts(self):
        """Save current prompts to storage."""
        if not self.is_service_available('prompt_manager'):
            self._output("Error: Prompt manager not available")
            return False

        try:
            self.service.prompt_manager.save_prompts()
            self._output("Prompts saved successfully")
            return True
        except Exception as e:
            self._output(f"Error saving prompts: {str(e)}")
            return False

    def reset_prompts(self):
        """Reset prompts to default values."""
        if not self.is_service_available('prompt_manager'):
            self._output("Error: Prompt manager not available")
            return False

        try:
            self.service.prompt_manager.reset_to_defaults()
            self._output("Prompts reset to defaults")
            return True
        except Exception as e:
            self._output(f"Error resetting prompts: {str(e)}")
            return False

    # --- Prompt Operations ---

    def execute_single_prompt(self, prompt_text: str):
        """
        Execute a single prompt synchronously and emit results.
        """
        if not prompt_text.strip():
            self._output("No prompt provided.")
            return
        self._output("Executing prompt...")

        try:
            responses = self.service.execute_prompt(prompt_text)
            for idx, response in enumerate(responses, start=1):
                self._output(f"Prompt #{idx} => {response}")
            self._output("Prompt execution complete.")
        except Exception as e:
            self._output(f"Error: {e}")

    def run_single_chat_mode(self, prompt_text: str):
        """
        Execute single prompt asynchronously in chat mode.
        """
        if not prompt_text.strip():
            self._output("No prompt text provided. Aborting execution.")
            return

        self._output("Launching single-chat mode...")

        def worker():
            try:
                responses = self.service.chat_manager.execute_prompts_single_chat([prompt_text], cycle_speed=2)
                for i, resp in enumerate(responses, start=1):
                    self._output(f"Prompt #{i}: {resp}")
                self._output("Single-chat execution completed.")
            except Exception as e:
                self._output(f"Error in single chat mode: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def run_multi_chat_mode(self, prompt_text: str, reverse_order: bool = False):
        """
        Execute multiple prompts across multiple chats asynchronously.
        """
        prompts = [line.strip() for line in prompt_text.splitlines() if line.strip()]
        if not prompts:
            self._output("No valid prompts provided.")
            return

        self._output("Launching multi-chat mode...")

        def worker():
            try:
                chats = self.service.chat_manager.get_all_chat_titles()
                if reverse_order:
                    chats.reverse()

                if not chats:
                    self._output("No chats found. Aborting.")
                    return

                for chat in chats:
                    chat_title = chat.get("title", "Untitled")
                    self._output(f"\nProcessing Chat: {chat_title}")

                    for idx, prompt in enumerate(prompts, start=1):
                        self._output(f"Sending Prompt #{idx}: {prompt}")
                        response = self.service.chat_manager.execute_prompt_cycle(prompt)
                        self._output(f"Response #{idx}: {response}")

                    self._output(f"Archiving chat: {chat_title}")
                    self.service.chat_manager.archive_chat(chat)

                self._output("Multi-chat execution complete.")

            except Exception as e:
                self._output(f"Error in multi-chat mode: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def start_prompt_cycle(self, selected_prompts: list, exclusions: list):
        """
        Run a full prompt cycle through the service.
        """
        self._output("Starting prompt cycle...")

        try:
            self.service.start_prompt_cycle(selected_prompts, exclusions)
            self._output("Prompt cycle completed.")
        except Exception as e:
            self._output(f"Error during prompt cycle: {e}")

    # --- Prompt Management ---

    def load_prompt(self, prompt_type: str):
        """
        Load a specific prompt configuration.
        """
        try:
            prompt_text, model = self.service.load_prompt(prompt_type)
            self._output(f"Loaded prompt '{prompt_type}' with model '{model}'.")
            return prompt_text, model
        except Exception as e:
            self._output(f"Error loading prompt: {e}")
            return "", ""

    def save_prompt(self, prompt_type: str, prompt_text: str):
        """
        Save updated prompt configuration.
        """
        try:
            self.service.save_prompt(prompt_type, prompt_text)
            self._output(f"Prompt '{prompt_type}' saved successfully.")
        except Exception as e:
            self._output(f"Error saving prompt '{prompt_type}': {e}")

    # --- Discord Bot Operations ---

    def launch_discord_bot(self, bot_token: str, channel_id: int):
        """
        Launch Discord bot with provided credentials.
        """
        try:
            self.service.launch_discord_bot(bot_token, channel_id, log_callback=self._discord_log)
            self._output("Discord bot launched.")
            self._update_status("Discord bot is running.")
        except Exception as e:
            self._output(f"Error launching Discord bot: {e}")

    def stop_discord_bot(self):
        """
        Stop running Discord bot.
        """
        try:
            self.service.stop_discord_bot()
            self._output("Discord bot stopped.")
            self._update_status("Discord bot is stopped.")
        except Exception as e:
            self._output(f"Error stopping Discord bot: {e}")

    # --- Reinforcement and Tuning ---

    def run_prompt_tuning(self):
        """
        Perform automatic prompt tuning using reinforcement data.
        """
        self._output("Starting prompt tuning...")

        try:
            self.service.run_prompt_tuning()
            last_updated = self.service.reinforcement_engine.memory_data.get('last_updated', 'unknown')
            self._output(f"Prompt tuning completed. Memory last updated: {last_updated}")
        except Exception as e:
            self._output(f"Error during prompt tuning: {e}")

    # --- Analysis Tools (Optional UI exposure) ---

    def analyze_execution_response(self, response: str, prompt_text: str):
        """
        Perform detailed response analysis (optional).
        """
        try:
            analysis = self.service.analyze_execution_response(response, prompt_text)
            self._output(f"Analysis: {analysis}")
        except Exception as e:
            self._output(f"Error analyzing response: {e}")

    # --- Lifecycle Management ---

    def shutdown(self):
        """
        Gracefully shut down services and clean resources.
        """
        try:
            self.service.shutdown_all()
            self._output("All services shut down cleanly.")
            self._update_status("Dreamscape system shutdown complete.")
        except Exception as e:
            self._output(f"Error during shutdown: {e}")
