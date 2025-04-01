# agent_dispatcher.py

import threading
import queue
import logging
import time
import sys
import os

# Add the core directory to sys.path dynamically
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Fixed imports
from ..chat_engine.chat_scraper_service import ChatScraperService as ChatScraperAgent
from ..services.prompt_execution_service import PromptService
from ..chat_engine.feedback_engine import FeedbackEngine
from ..chat_engine.discord_dispatcher import DiscordDispatcher
from ..DriverManager import DriverManager

logger = logging.getLogger("AgentDispatcher")
logger.setLevel(logging.INFO)

class AgentDispatcher:
    """
    Orchestrates and manages all system agents. Handles task distribution,
    lifecycle management, and communication between agents.
    """

    def __init__(self, config):
        logger.info(" Initializing AgentDispatcher...")

        # Core config
        self.config = config
        self.task_queue = queue.Queue()
        self.running = False

        # Driver shared across agents
        self.driver_manager = DriverManager(headless=self.config.get("headless", True))

        # Initialize agents
        self.scraper_agent = ChatScraperAgent(self.driver_manager)
        self.prompt_executor = PromptService(model=self.config.get("default_model", "gpt-4o-mini"))
        self.feedback_engine = FeedbackEngine(memory_file=self.config.get("memory_file", "memory/persistent_memory.json"))
        self.discord_dispatcher = DiscordDispatcher(
            token=self.config.get("discord_token", ""),
            default_channel_id=int(self.config.get("discord_channel_id", 0))
        )

        logger.info(" AgentDispatcher initialized successfully.")

    # ---------------------------------------------------
    # DISPATCHER LIFECYCLE
    # ---------------------------------------------------

    def start(self):
        logger.info(" Starting AgentDispatcher...")

        # Boot up Discord bot (if enabled)
        if self.config.get("discord_enabled", False):
            threading.Thread(target=self.discord_dispatcher.run_bot, daemon=True).start()

        # Start agents (scraper runs in its own thread)
        threading.Thread(target=self.scraper_agent.run, daemon=True).start()

        self.running = True
        self.event_loop()

    def stop(self):
        logger.info(" Stopping AgentDispatcher...")

        self.running = False
        self.scraper_agent.stop()
        self.discord_dispatcher.shutdown()
        self.driver_manager.shutdown_driver()

    def event_loop(self):
        logger.info(" Starting AgentDispatcher event loop...")
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                self._handle_task(task)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f" Error in event loop: {e}")

    # ---------------------------------------------------
    # TASK DISPATCH
    # ---------------------------------------------------

    def add_task(self, task):
        """Enqueue a task for execution."""
        logger.info(f" Received new task: {task.get('action', 'unknown')}")
        self.task_queue.put(task)

    def _handle_task(self, task):
        """Handles task routing and execution."""
        action = task.get("action")

        if action == "scrape_chats":
            self.scraper_agent.receive_task(task)

        elif action == "execute_prompts":
            chat = task.get("chat")
            prompt_list = task.get("prompts", [])

            threading.Thread(
                target=self._execute_prompts_on_chat,
                args=(chat, prompt_list),
                daemon=True
            ).start()

        elif action == "memory_review":
            self._review_memory()

        elif action == "send_discord_message":
            channel = task.get("channel")
            message = task.get("message")
            self.discord_dispatcher.send_message(channel, message)

        else:
            logger.warning(f"️ Unknown action: {action}")

    # ---------------------------------------------------
    # INTERNAL TASKS
    # ---------------------------------------------------

    def _execute_prompts_on_chat(self, chat, prompt_list):
        chat_title = chat.get("title", "Untitled")
        chat_link = chat.get("link")

        logger.info(f" Executing prompts on chat: {chat_title}")

        if not chat_link:
            logger.warning(f" Chat '{chat_title}' has no link. Aborting.")
            return

        # Load chat in browser
        self.scraper_agent.load_chat(chat_link)
        time.sleep(2)

        # Loop through prompts
        for prompt_name in prompt_list:
            logger.info(f" Executing prompt '{prompt_name}' on chat '{chat_title}'")
            prompt_text = self.prompt_executor.get_prompt(prompt_name)
            response = self.prompt_executor.execute_prompt_cycle(prompt_text)

            if not response:
                logger.warning(f"️ No response for prompt '{prompt_name}' on chat '{chat_title}'")
                continue

            # Analyze + feedback
            memory_update = self.feedback_engine.parse_and_update_memory(response)
            if memory_update:
                logger.info(f"🧠 Memory updated with: {memory_update}")
                self.discord_dispatcher.dispatch_memory_update(memory_update)

            # Discord notification
            self.discord_dispatcher.send_message("dreamscape", f"New response from {chat_title}:\n{response[:2000]}")

    def _review_memory(self):
        """Trigger a memory review and send to Discord."""
        review = self.feedback_engine.review_memory()
        self.discord_dispatcher.send_message("dreamscape", f"🧠 Memory Review:\n{review}")

