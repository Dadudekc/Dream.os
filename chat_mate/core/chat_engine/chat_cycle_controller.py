import os
import time
import json
import logging
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional

# UTILS
from core.FileManager import FileManager
from core.config.config_manager import ConfigManager
from core.services.output_handler import OutputHandler

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
        logger.info(" Initializing ChatCycleController...")

        # CONFIG INITIALIZATION
        self.config = ConfigManager(config_path)
        self.model = self.config.get("default_model", "gpt-4o-mini")
        self.output_dir = self.config.get("output_dir", "responses")
        self.reverse_order = self.config.get("reverse_order", False)
        self.archive_enabled = self.config.get("archive_enabled", True)

        # Initialize OutputHandler
        self.output_handler = OutputHandler(
            logger=logger,
            output_callbacks=[output_callback] if output_callback else None,
            output_dir=os.path.join(self.output_dir, "logs")
        )

        # SERVICES (Override if provided)
        self.driver_manager = driver_manager
        self.scraper = chat_scraper
        self.executor = prompt_executor
        self.feedback_engine = feedback_engine
        self.discord = discord_dispatcher

        # Only initialize services if they were not passed in
        if not self.scraper:
            from core.chat_engine.chat_scraper_service import ChatScraperService
            self.scraper = ChatScraperService(headless=self.config.get("headless", True))
            
        if not self.executor:
            from core.services.prompt_execution_service import PromptService
            self.executor = PromptService(model=self.model)
            
        if not self.feedback_engine:
            from core.chat_engine.feedback_engine import FeedbackEngine
            self.feedback_engine = FeedbackEngine(
                memory_file=self.config.get("memory_file", "memory/persistent_memory.json")
            )
            
        if not self.discord:
            from core.chat_engine.discord_dispatcher import DiscordDispatcher
            self.discord = DiscordDispatcher(
                token=self.config.get("discord_token", ""),
                default_channel_id=int(self.config.get("discord_channel_id", 0))
            )

        self.excluded_chats = set(self.config.get("excluded_chats", []))

        logger.info(" ChatCycleController initialized.")
        self.output_handler.info("🚀 ChatCycleController initialized and ready.")

    # ---------------------------------------------------
    # OUTPUT HANDLING
    # ---------------------------------------------------

    def append_output(self, message: str, level: str = "info", metadata: Optional[Dict[str, Any]] = None):
        """
        Centralized output method using OutputHandler.
        
        Args:
            message: The message to output
            level: Log level (info, warning, error, debug)
            metadata: Optional metadata to attach
        """
        self.output_handler.output(message, level, metadata)

    # ---------------------------------------------------
    # SYSTEM EXECUTION SEQUENCES
    # ---------------------------------------------------

    def start(self):
        """
        Starts the chat cycle orchestration loop.
        """
        logger.info(" Starting chat cycle controller...")
        self.append_output("🚀 Chat cycle starting...")

        # Start Discord bot in a thread if enabled
        if self.config.get("discord_enabled", False):
            threading.Thread(target=self.discord.run_bot, daemon=True).start()

        # Scrape and process chats
        chat_list = self.scraper.get_all_chats(excluded_chats=self.excluded_chats)

        if not chat_list:
            self.append_output("❗ No chats found. Aborting cycle.", "warning")
            return

        if self.reverse_order:
            chat_list.reverse()
            self.append_output("🔄 Reversing chat order...")

        logger.info(f" {len(chat_list)} chats ready for processing.")
        self.append_output(f"📋 {len(chat_list)} chats ready for processing.", metadata={"chat_count": len(chat_list)})

        for chat in chat_list:
            self.process_chat(chat)

        logger.info(" Chat cycle complete.")
        self.append_output("✅ Chat cycle complete.")

    def process_chat(self, chat):
        """
        Executes prompts on a single chat, processes responses, updates memory, and dispatches feedback.
        Uses the new orchestration capabilities for efficient batch processing.
        """
        chat_title = chat.get("title", "Untitled")
        chat_link = chat.get("link")

        logger.info(f"--- Processing chat: {chat_title} ---")
        self.append_output(f"\n--- Processing chat: {chat_title} ---", metadata={"chat_title": chat_title, "chat_link": chat_link})

        if not chat_link:
            logger.warning(f"️ Missing chat link for {chat_title}. Skipping.")
            self.append_output(f"⚠️ Missing chat link for {chat_title}. Skipping.", "warning")
            return

        self.scraper.load_chat(chat_link)
        time.sleep(2)

        # Retrieve prompt names from config and prepare batch queue
        prompt_names = self.config.get("prompt_cycle", [])
        queued_prompts = []
        cycle_start_time = time.time()

        # Prepare the queue of prompts
        for prompt_name in prompt_names:
            logger.info(f" Loading prompt: {prompt_name} for chat: {chat_title}")
            self.append_output(f"📝 Loading prompt: {prompt_name} for chat: {chat_title}")

            try:
                prompt_text = self.executor.get_prompt(prompt_name)
                queued_prompts.append({
                    "name": prompt_name,
                    "text": prompt_text
                })
            except Exception as e:
                logger.error(f" Failed to load prompt '{prompt_name}': {e}")
                self.append_output(f"❌ Failed to load prompt '{prompt_name}': {e}", "error")
                
        # If there are no valid prompts, skip this chat
        if not queued_prompts:
            logger.warning(f" No valid prompts loaded for {chat_title}. Skipping.")
            self.append_output(f"⚠️ No valid prompts loaded for {chat_title}. Skipping.", "warning")
            return
            
        # Check if we can retrieve project context for enhanced prompts
        context = self.retrieve_project_context(chat_title)
        if context:
            logger.info(f" Injecting context for {chat_title}")
            self.append_output(f"🧠 Injecting context for {chat_title}", metadata={"context_keys": list(context.keys())})
            if hasattr(self.executor, 'inject_context'):
                self.executor.inject_context(context)
            else:
                logger.warning(f" Executor doesn't support context injection")
                
        # Execute the prompt queue as a batch if supported
        chat_responses = []
        if hasattr(self.executor, 'queue_prompts'):
            logger.info(f" Executing {len(queued_prompts)} prompts as batch for {chat_title}")
            self.append_output(f"🔄 Executing {len(queued_prompts)} prompts as batch for {chat_title}")
            
            # Extract just the text for the queue_prompts method
            prompt_texts = [p["text"] for p in queued_prompts]
            
            # Execute the batch
            responses = self.executor.queue_prompts(prompt_texts)
            
            # Match responses back to prompt names
            for i, response in enumerate(responses):
                if i < len(queued_prompts):
                    prompt_name = queued_prompts[i]["name"]
                    chat_responses.append({
                        "prompt_name": prompt_name,
                        "response": response,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Save individual response
                    self._save_prompt_response(chat_title, prompt_name, response)
                    
                    # Process memory update for this response
                    memory_update = self.feedback_engine.parse_response_for_memory_update(response)
                    self.feedback_engine.update_memory(memory_update)
                    
                    # Handle Discord dispatch
                    if prompt_name.lower() == "dreamscape":
                        self.discord.dispatch_dreamscape_episode(chat_title, response)
                    else:
                        self.discord.dispatch_general_response(chat_title, prompt_name, response)
        else:
            # Fall back to sequential processing
            logger.info(f" Falling back to sequential processing for {chat_title}")
            for prompt_info in queued_prompts:
                prompt_name = prompt_info["name"]
                prompt_text = prompt_info["text"]
                
                logger.info(f" Executing prompt: {prompt_name} on chat: {chat_title}")
                self.append_output(f"📝 Executing prompt: {prompt_name} on chat: {chat_title}")
                
                response = self.executor.send_prompt_and_wait(prompt_text)
                
                if not response:
                    logger.warning(f"️ No stable response for {prompt_name} in {chat_title}")
                    self.append_output(f"⚠️ No stable response for {prompt_name} in {chat_title}", "warning")
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
                
                # Discord dispatch
                if prompt_name.lower() == "dreamscape":
                    self.discord.dispatch_dreamscape_episode(chat_title, response)
                else:
                    self.discord.dispatch_general_response(chat_title, prompt_name, response)
                
                time.sleep(1)
        
        cycle_end_time = time.time()
        execution_time = round(cycle_end_time - cycle_start_time, 2)

        # Aggregate chat run metadata and save
        run_metadata = {
            "timestamp": datetime.now().isoformat(),
            "execution_time": f"{execution_time}s",
            "chat_title": chat_title,
            "model": self.model,
            "prompt_count": len(prompt_names)
        }

        self._save_run_summary(chat_title, chat_responses, run_metadata)
        
        # Run post-cycle analysis if executor supports it
        self.post_cycle_analysis(chat_title)

        # Archive chat if enabled
        if self.archive_enabled:
            self.scraper.archive_chat(chat)
            self.append_output(f"📦 Archived chat: {chat_title}")

        logger.info(f" Completed processing for {chat_title}")
        self.append_output(f"✅ Completed processing for {chat_title}", metadata={"execution_time": execution_time})

    # ---------------------------------------------------
    # SINGLE CHAT MODE
    # ---------------------------------------------------

    def run_single_chat(self, chat_link, prompt_name):
        """
        Runs a prompt on a single chat.
        """
        chat_title = chat_link.split("/")[-1] or "Untitled"
        logger.info(f" Running single prompt '{prompt_name}' on chat: {chat_title}")
        self.append_output(f"🔍 Running single prompt '{prompt_name}' on chat: {chat_title}")

        self.scraper.load_chat(chat_link)
        time.sleep(2)

        try:
            prompt_text = self.executor.get_prompt(prompt_name)
        except Exception as e:
            logger.error(f" Failed to load prompt '{prompt_name}': {e}")
            self.append_output(f"❌ Failed to load prompt '{prompt_name}': {e}", "error")
            return

        # Check if context injection is supported and context is available
        context = self.retrieve_project_context(chat_title)
        if context and hasattr(self.executor, 'inject_context'):
            self.executor.inject_context(context)
            self.append_output(f"🧠 Injected context for {chat_title}")

        # Use execute_prompt_cycle if available
        if hasattr(self.executor, 'execute_prompt_cycle'):
            response = self.executor.execute_prompt_cycle(prompt_text)
        else:
            response = self.executor.send_prompt_and_wait(prompt_text)

        if not response:
            logger.warning(f"️ No response from chat '{chat_title}'")
            self.append_output(f"⚠️ No response from chat '{chat_title}'", "warning")
            return

        self._save_prompt_response(chat_title, prompt_name, response)

        memory_update = self.feedback_engine.parse_response_for_memory_update(response)
        self.feedback_engine.update_memory(memory_update)

        if prompt_name.lower() == "dreamscape":
            self.discord.dispatch_dreamscape_episode(chat_title, response)
        else:
            self.discord.dispatch_general_response(chat_title, prompt_name, response)

        logger.info(f" Single chat execution complete for: {chat_title}")
        self.append_output(f"✅ Single chat execution complete for: {chat_title}")

    # ---------------------------------------------------
    # ORCHESTRATION ENHANCEMENTS
    # ---------------------------------------------------
    
    def retrieve_project_context(self, chat_title: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve external context such as project analysis or memory snapshot.
        """
        try:
            # Try to get context from a ProjectScanner if available
            try:
                from core.ProjectScanner import ProjectScanner
                scanner = ProjectScanner()
                context = scanner.get_context(chat_title)
                logger.info(f" Retrieved context for {chat_title}: {list(context.keys()) if context else None}")
                return context
            except ImportError:
                # If ProjectScanner isn't available, try creating basic context
                context = {
                    "chat_title": chat_title,
                    "timestamp": datetime.now().isoformat(),
                    "model": self.model
                }
                
                # Try to add memory data if available
                if hasattr(self.feedback_engine, 'get_memory_snapshot'):
                    memory_snapshot = self.feedback_engine.get_memory_snapshot()
                    if memory_snapshot:
                        context["memory"] = memory_snapshot
                
                return context
        except Exception as e:
            logger.error(f" Failed to retrieve context for {chat_title}: {e}")
            return None
            
    def post_cycle_analysis(self, chat_title: str):
        """
        After processing a chat, aggregate responses and run analysis to 
        determine if further iterations or corrections are needed.
        """
        # Only run analysis if the executor supports getting the last response
        if not hasattr(self.executor, 'get_last_response'):
            return
            
        final_response = self.executor.get_last_response()
        if not final_response:
            logger.warning(f" No final response available for {chat_title}")
            return
            
        # Run analysis on the response
        if hasattr(self.executor, 'analyze_execution_response'):
            analysis = self.executor.analyze_execution_response(final_response, "Aggregated Prompt Cycle")
            logger.info(f" Post-cycle analysis for {chat_title}: {analysis}")
            self.append_output(f"📊 Post-cycle analysis for {chat_title}: {analysis}", metadata={"analysis": analysis})
            
            # Optionally, trigger a re-run or additional prompt cycle based on analysis
            if analysis.get("length", 0) < 100:
                logger.warning(f" Response for {chat_title} seems too short. Consider reprocessing.")
                self.append_output(f"⚠️ Response for {chat_title} seems too short. Consider reprocessing.", "warning")
        else:
            # Basic analysis if the executor doesn't support it
            basic_analysis = {
                "length": len(final_response),
                "has_code": "```" in final_response
            }
            logger.info(f" Basic post-cycle analysis for {chat_title}: {basic_analysis}")

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
            logger.info(f" Saved response: {file_path}")
        except Exception as e:
            logger.error(f" Failed to save response file {file_path}: {e}")

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
            logger.info(f" Full run summary saved: {file_path}")
        except Exception as e:
            logger.error(f" Failed to save run summary {file_path}: {e}")

    # ---------------------------------------------------
    # SHUTDOWN
    # ---------------------------------------------------

    def shutdown(self):
        """
        Shuts down services cleanly.
        """
        logger.info(" Shutting down ChatCycleController...")
        self.append_output("🛑 Shutting down ChatCycleController...")
        self.scraper.shutdown()
        self.discord.shutdown()
        self.append_output("✅ ChatCycleController shut down successfully.")


# ---------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------

def sanitize_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)


if __name__ == "__main__":
    controller = ChatCycleController(config_path="config.json")
    controller.start()
