import os
import time
import json
import logging
import threading
from datetime import datetime

# SERVICES
from core.chat_engine.chat_scraper_service import ChatScraperService
from core.chat_engine.prompt_execution_service import PromptExecutionService
from core.chat_engine.feedback_engine import FeedbackEngine
from core.chat_engine.discord_dispatcher import DiscordDispatcher

# UTILS
from core.FileManager import FileManager
from chat_mate_config import Config

logger = logging.getLogger("ChatCycleController")
logger.setLevel(logging.INFO)


class ChatCycleController:
    """
    Master orchestrator for chat scraping, prompt cycles,
    memory updates, and Discord dispatching.
    """

    def __init__(
        self,
        driver_manager=None,
        prompt_executor=None,
        chat_scraper=None,
        feedback_engine=None,
        discord_dispatcher=None,
        config_path="config.json",
        output_callback=None
    ):
        logger.info("⚡ Initializing ChatCycleController...")

        # OUTPUT HANDLING
        self.output_callback = output_callback or self._default_output_callback

        # CONFIG INITIALIZATION
        self.config = Config(config_path)
        self.model = self.config.get("default_model", "gpt-4o-mini")
        self.output_dir = self.config.get("output_dir", "responses")
        self.reverse_order = self.config.get("reverse_order", False)
        self.archive_enabled = self.config.get("archive_enabled", True)

        # SERVICES (Override if provided)
        self.driver_manager = driver_manager
        self.scraper = chat_scraper or ChatScraperService(headless=self.config.get("headless", True))
        self.executor = prompt_executor or PromptExecutionService(model=self.model)
        self.feedback_engine = feedback_engine or FeedbackEngine(
            memory_file=self.config.get("memory_file", "memory/persistent_memory.json")
        )
        self.discord = discord_dispatcher or DiscordDispatcher(
            token=self.config.get("discord_token", ""),
            default_channel_id=int(self.config.get("discord_channel_id", 0))
        )

        self.excluded_chats = set(self.config.get("excluded_chats", []))

        logger.info("✅ ChatCycleController initialized.")

    # ---------------------------------------------------
    # OUTPUT HANDLING
    # ---------------------------------------------------

    def _default_output_callback(self, message: str):
        print(message)

    def append_output(self, message: str):
        if self.output_callback:
            self.output_callback(message)
        else:
            print(message)

    # ---------------------------------------------------
    # SYSTEM EXECUTION SEQUENCES
    # ---------------------------------------------------

    def start(self):
        """
        Starts the chat cycle orchestration loop.
        """
        logger.info("🚀 Starting chat cycle controller...")
        self.append_output("🚀 Chat cycle starting...")

        # Start Discord bot in a thread if enabled
        if self.config.get("discord_enabled", False):
            threading.Thread(target=self.discord.run_bot, daemon=True).start()

        # Scrape and process chats
        chat_list = self.scraper.get_all_chats(excluded_chats=self.excluded_chats)

        if not chat_list:
            self.append_output("❗ No chats found. Aborting cycle.")
            return

        if self.reverse_order:
            chat_list.reverse()
            self.append_output("🔄 Reversing chat order...")

        logger.info(f"📋 {len(chat_list)} chats ready for processing.")
        self.append_output(f"📋 {len(chat_list)} chats ready for processing.")

        for chat in chat_list:
            self.process_chat(chat)

        logger.info("✅ Chat cycle complete.")
        self.append_output("✅ Chat cycle complete.")

    def process_chat(self, chat):
        """
        Executes prompts on a single chat, processes responses, updates memory, and dispatches feedback.
        """
        chat_title = chat.get("title", "Untitled")
        chat_link = chat.get("link")

        logger.info(f"--- Processing chat: {chat_title} ---")
        self.append_output(f"\n--- Processing chat: {chat_title} ---")

        if not chat_link:
            logger.warning(f"⚠️ Missing chat link for {chat_title}. Skipping.")
            self.append_output(f"⚠️ Missing chat link for {chat_title}. Skipping.")
            return

        self.scraper.load_chat(chat_link)
        time.sleep(2)

        prompt_names = self.config.get("prompt_cycle", [])
        chat_responses = []
        cycle_start_time = time.time()

        for prompt_name in prompt_names:
            logger.info(f"📝 Executing prompt: {prompt_name} on chat: {chat_title}")
            self.append_output(f"📝 Executing prompt: {prompt_name} on chat: {chat_title}")

            try:
                prompt_text = self.executor.get_prompt(prompt_name)
            except Exception as e:
                logger.error(f"❌ Failed to load prompt '{prompt_name}': {e}")
                self.append_output(f"❌ Failed to load prompt '{prompt_name}': {e}")
                continue

            response = self.executor.send_prompt_and_wait(prompt_text)

            if not response:
                logger.warning(f"⚠️ No stable response for {prompt_name} in {chat_title}")
                self.append_output(f"⚠️ No stable response for {prompt_name} in {chat_title}")
                continue

            chat_responses.append({
                "prompt_name": prompt_name,
                "response": response,
                "timestamp": datetime.now().isoformat()
            })

            # Save response
            self._save_prompt_response(chat_title, prompt_name, response)

            # Feedback Engine updates
            memory_update = self.feedback_engine.parse_response_for_memory_update(response)
            self.feedback_engine.update_memory(memory_update)

            # Discord dispatch (if dreamscape)
            if prompt_name.lower() == "dreamscape":
                self.discord.dispatch_dreamscape_episode(chat_title, response)
            else:
                self.discord.dispatch_general_response(chat_title, prompt_name, response)

            time.sleep(1)

        cycle_end_time = time.time()

        # Aggregate chat run metadata and save
        run_metadata = {
            "timestamp": datetime.now().isoformat(),
            "execution_time": f"{round(cycle_end_time - cycle_start_time, 2)}s",
            "chat_title": chat_title,
            "model": self.model,
            "prompt_count": len(prompt_names)
        }

        self._save_run_summary(chat_title, chat_responses, run_metadata)

        # Archive chat if enabled
        if self.archive_enabled:
            self.scraper.archive_chat(chat)
            self.append_output(f"📦 Archived chat: {chat_title}")

        logger.info(f"✅ Completed processing for {chat_title}")
        self.append_output(f"✅ Completed processing for {chat_title}")

    # ---------------------------------------------------
    # SINGLE CHAT MODE
    # ---------------------------------------------------

    def run_single_chat(self, chat_link, prompt_name):
        """
        Runs a prompt on a single chat.
        """
        chat_title = chat_link.split("/")[-1] or "Untitled"
        logger.info(f"🔍 Running single prompt '{prompt_name}' on chat: {chat_title}")
        self.append_output(f"🔍 Running single prompt '{prompt_name}' on chat: {chat_title}")

        self.scraper.load_chat(chat_link)
        time.sleep(2)

        try:
            prompt_text = self.executor.get_prompt(prompt_name)
        except Exception as e:
            logger.error(f"❌ Failed to load prompt '{prompt_name}': {e}")
            self.append_output(f"❌ Failed to load prompt '{prompt_name}': {e}")
            return

        response = self.executor.send_prompt_and_wait(prompt_text)

        if not response:
            logger.warning(f"⚠️ No response from chat '{chat_title}'")
            self.append_output(f"⚠️ No response from chat '{chat_title}'")
            return

        self._save_prompt_response(chat_title, prompt_name, response)

        memory_update = self.feedback_engine.parse_response_for_memory_update(response)
        self.feedback_engine.update_memory(memory_update)

        if prompt_name.lower() == "dreamscape":
            self.discord.dispatch_dreamscape_episode(chat_title, response)
        else:
            self.discord.dispatch_general_response(chat_title, prompt_name, response)

        logger.info(f"✅ Single chat execution complete for: {chat_title}")
        self.append_output(f"✅ Single chat execution complete for: {chat_title}")

    # ---------------------------------------------------
    # HELPERS
    # ---------------------------------------------------

    def _save_prompt_response(self, chat_title, prompt_name, response):
        """
        Saves individual prompt responses to file.
        """
        prompt_dir = os.path.join(self.output_dir, sanitize_filename(chat_title), sanitize_filename(prompt_name))
        os.makedirs(prompt_dir, exist_ok=True)

        filename = f"{sanitize_filename(chat_title)}_{sanitize_filename(prompt_name)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path = os.path.join(prompt_dir, filename)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(response)
            logger.info(f"💾 Saved response: {file_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save response file {file_path}: {e}")

    def _save_run_summary(self, chat_title, chat_responses, metadata):
        """
        Saves a full summary of the prompt cycle run.
        """
        summary_dir = os.path.join(self.output_dir, sanitize_filename(chat_title))
        os.makedirs(summary_dir, exist_ok=True)

        filename = f"{sanitize_filename(chat_title)}_full_run.json"
        file_path = os.path.join(summary_dir, filename)

        full_run_data = {
            "metadata": metadata,
            "responses": chat_responses
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(full_run_data, f, indent=4, ensure_ascii=False)
            logger.info(f"📦 Full run summary saved: {file_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save run summary {file_path}: {e}")

    # ---------------------------------------------------
    # SHUTDOWN
    # ---------------------------------------------------

    def shutdown(self):
        """
        Shuts down services cleanly.
        """
        logger.info("🛑 Shutting down ChatCycleController...")
        self.scraper.shutdown()
        self.discord.shutdown()


# ---------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------

def sanitize_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)


if __name__ == "__main__":
    controller = ChatCycleController(config_path="config.json")
    controller.start()
