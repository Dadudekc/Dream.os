# chat_scraper_agent.py

import time
import logging
from core.Agents.base_agent import BaseAgent
from core.DriverManager import DriverManager  # Reuse existing manager if available

logger = logging.getLogger("ChatScraperAgent")

class ChatScraperAgent(BaseAgent):
    """
    ChatScraperAgent: Autonomous agent responsible for scraping chat metadata.
    """

    def __init__(self, driver_manager: DriverManager, name="ChatScraperAgent"):
        super().__init__(name)
        self.driver_manager = driver_manager
        self.driver = self.driver_manager.get_driver()

    # ---------------------------------------------
    # Core Task Handler
    # ---------------------------------------------
    def handle_task(self, task: dict):
        action = task.get("action")
        
        if action == "scrape_chats":
            filters = task.get("filters", {})
            chats = self.get_all_chats(filters=filters)
            
            logger.info(f"[{self.name}] Scraped {len(chats)} chats.")
            
            # Return chats to task initiator (if needed)
            if "callback" in task and callable(task["callback"]):
                task["callback"](chats)

        elif action == "validate_login":
            logged_in = self.validate_login()
            logger.info(f"[{self.name}] Login status: {'' if logged_in else ''}")
        
        else:
            logger.warning(f"[{self.name}] Unknown action: {action}")

    # ---------------------------------------------
    # Chat Scraping Functions
    # ---------------------------------------------
    def get_all_chats(self, filters=None):
        """
        Scrapes all available chat titles and links.
        Optionally filters chats.
        """
        logger.info(f"[{self.name}] Collecting chats...")
        chats = []  # Your scraping logic here
        
        # Example structure (replace this with actual scraping results)
        chats = [
            {"title": "Chat A", "link": "https://chat.link/a"},
            {"title": "Chat B", "link": "https://chat.link/b"},
        ]

        if filters:
            chats = self.filter_chats(chats, filters)

        return chats

    def filter_chats(self, chats, filters):
        """
        Apply filters such as exclusions or search criteria.
        """
        logger.info(f"[{self.name}] Filtering chats with: {filters}")
        # Example: Exclude by title keyword
        exclude_keyword = filters.get("exclude_keyword")
        if exclude_keyword:
            chats = [c for c in chats if exclude_keyword not in c["title"]]

        return chats

    def validate_login(self):
        """
        Verify login status via driver logic.
        """
        logger.info(f"[{self.name}] Validating login...")
        return self.driver_manager.is_logged_in()

    # ---------------------------------------------
    # Optional Manual Login Trigger (blocking)
    # ---------------------------------------------
    def manual_login_flow(self):
        """
        Manual login for user if auto-login fails.
        """
        logger.warning(f"[{self.name}] Manual login required. Waiting for user...")
        self.driver.get("https://chat.openai.com/")
        time.sleep(30)  # Allow user to log in manually
        return self.validate_login()
