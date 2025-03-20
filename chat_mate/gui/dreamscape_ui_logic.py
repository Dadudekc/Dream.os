import threading
from gui.dreamscape_services import DreamscapeService

class DreamscapeUILogic:
    """
    Bridges UI interactions with backend services.
    """

    def __init__(self, output_callback):
        """
        Initializes the UILogic with service connections and UI callbacks.

        :param output_callback: Callable for sending text messages to UI (e.g., appending logs)
        """
        self.output = output_callback
        self.service = DreamscapeService()

    # --- Prompt Operations ---

    def execute_single_prompt(self, prompt_text: str):
        """
        Execute a single prompt synchronously and output results.
        """
        if not prompt_text.strip():
            self.output("No prompt provided.")
            return
        self.output("Executing prompt...")
        try:
            responses = self.service.execute_prompt(prompt_text)
            for idx, response in enumerate(responses, start=1):
                self.output(f"Prompt #{idx} => {response}")
            self.output("Prompt execution complete.")
        except Exception as e:
            self.output(f"Error: {e}")

    def run_single_chat_mode(self, prompt_text: str):
        """
        Execute single prompt asynchronously in chat mode.
        """
        if not prompt_text.strip():
            self.output("No prompt text provided. Aborting execution.")
            return
        self.output("Launching single-chat mode...")

        def worker():
            responses = self.service.chat_manager.execute_prompts_single_chat([prompt_text], cycle_speed=2)
            for i, resp in enumerate(responses, start=1):
                self.output(f"Prompt #{i}: {resp}")
            self.output("Single-chat execution completed.")

        threading.Thread(target=worker, daemon=True).start()

    def run_multi_chat_mode(self, prompt_text: str, reverse_order: bool = False):
        """
        Execute multiple prompts across multiple chats asynchronously.
        """
        prompts = [line.strip() for line in prompt_text.splitlines() if line.strip()]
        if not prompts:
            self.output("No valid prompts provided.")
            return
        self.output("Launching multi-chat mode...")

        def worker():
            chats = self.service.chat_manager.get_all_chat_titles()
            if reverse_order:
                chats.reverse()

            if not chats:
                self.output("No chats found. Aborting.")
                return

            for chat in chats:
                chat_title = chat.get("title", "Untitled")
                self.output(f"\nProcessing Chat: {chat_title}")
                for idx, prompt in enumerate(prompts, start=1):
                    self.output(f"Sending Prompt #{idx}: {prompt}")
                    response = self.service.chat_manager.execute_prompt_cycle(prompt)
                    self.output(f"Response #{idx}: {response}")
                self.output(f"Archiving chat: {chat_title}")
                self.service.chat_manager.archive_chat(chat)

            self.output("Multi-chat execution complete.")

        threading.Thread(target=worker, daemon=True).start()

    def start_prompt_cycle(self, selected_prompts: list, exclusions: list):
        """
        Run a full prompt cycle through the service.
        """
        self.output("Starting prompt cycle...")
        self.service.start_prompt_cycle(selected_prompts, exclusions)
        self.output("Prompt cycle completed.")

    # --- Prompt Management ---

    def load_prompt(self, prompt_type: str):
        """
        Load a specific prompt configuration.
        """
        try:
            prompt_text, model = self.service.load_prompt(prompt_type)
            self.output(f"Loaded prompt '{prompt_type}' with model '{model}'.")
            return prompt_text, model
        except Exception as e:
            self.output(f"Error loading prompt: {e}")
            return "", ""

    def save_prompt(self, prompt_type: str, prompt_text: str):
        """
        Save updated prompt configuration.
        """
        self.service.save_prompt(prompt_type, prompt_text)
        self.output(f"Prompt '{prompt_type}' saved successfully.")

    def reset_prompts(self):
        """
        Reset all prompts to defaults.
        """
        self.service.reset_prompts()
        self.output("Prompts reset to defaults.")

    # --- Discord Bot Operations ---

    def launch_discord_bot(self, bot_token: str, channel_id: int):
        """
        Launch Discord bot with provided credentials.
        """
        self.service.launch_discord_bot(bot_token, channel_id, log_callback=self.output)
        self.output("Discord bot launched.")

    def stop_discord_bot(self):
        """
        Stop running Discord bot.
        """
        self.service.stop_discord_bot()
        self.output("Discord bot stopped.")

    # --- Reinforcement and Tuning ---

    def run_prompt_tuning(self):
        """
        Perform automatic prompt tuning using reinforcement data.
        """
        self.output("Starting prompt tuning...")
        self.service.run_prompt_tuning()
        last_updated = self.service.reinforcement_engine.memory_data.get('last_updated', 'unknown')
        self.output(f"Prompt tuning completed. Memory last updated: {last_updated}")

    # --- Analysis Tools (Optional UI exposure) ---

    def analyze_execution_response(self, response: str, prompt_text: str):
        """
        Perform detailed response analysis (optional).
        """
        analysis = self.service.analyze_execution_response(response, prompt_text)
        self.output(f"Analysis: {analysis}")

    # --- Lifecycle Management ---

    def shutdown(self):
        """
        Gracefully shut down services and clean resources.
        """
        self.service.shutdown_all()
        self.output("All services shut down cleanly.")
