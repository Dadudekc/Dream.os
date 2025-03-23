# chat_scraper_service.py

import time
import logging

logger = logging.getLogger("ChatScraper")

class ChatScraperService:
    """
    ChatScraperService retrieves available chat titles and links from the chat UI.
    It handles exclusions and filtering for downstream execution cycles.
    """

    def __init__(self, driver_manager, exclusions=None, reverse_order=False):
        self.driver_manager = driver_manager
        self.driver = self.driver_manager.driver
        self.exclusions = exclusions if exclusions else []
        self.reverse_order = reverse_order

    def get_all_chats(self) -> list:
        """
        Retrieves all chat titles and links available in the sidebar.
        Returns a list of dictionaries with 'title' and 'link'.
        """
        logger.info(" Scraping all chats from sidebar...")
        try:
            time.sleep(2)  # Give time for elements to load
            chat_elements = self.driver.find_elements("xpath", "//a[contains(@class, 'group') and contains(@href, '/c/')]")
            
            if not chat_elements:
                logger.warning("️ No chats found in the sidebar.")
                return []

            chats = []
            for el in chat_elements:
                title = el.text.strip() or "Untitled"
                link = el.get_attribute("href")
                if not link:
                    logger.warning(f"️ Chat '{title}' has no link, skipping.")
                    continue
                chats.append({"title": title, "link": link})

            logger.info(f" Retrieved {len(chats)} chats from sidebar.")
            return chats

        except Exception as e:
            logger.error(f" Error while scraping chats: {e}")
            return []

    def get_filtered_chats(self) -> list:
        """
        Filters out chats listed in self.exclusions.
        Can reverse order if self.reverse_order is True.
        """
        all_chats = self.get_all_chats()
        logger.info(f" Filtering {len(all_chats)} chats...")

        filtered = [
            chat for chat in all_chats
            if chat["title"] not in self.exclusions
        ]

        logger.info(f" {len(filtered)} chats after exclusion filter.")

        if self.reverse_order:
            filtered.reverse()
            logger.info(" Reversed chat order as requested.")

        return filtered

    def validate_login(self) -> bool:
        """
        Checks if the user is logged in based on the presence of sidebar elements.
        """
        logger.info(" Validating OpenAI chat login status...")
        try:
            sidebar = self.driver.find_element("xpath", "//nav[contains(@class, 'flex h-full')]")
            if sidebar:
                logger.info(" User is logged in.")
                return True
        except Exception:
            logger.warning("️ User is NOT logged in or sidebar is missing.")
        return False

    def manual_login_flow(self):
        """
        Prompts the user to manually log in via the browser.
        """
        logger.info(" Manual login flow initiated. Waiting for user login...")
        self.driver.get("https://chat.openai.com/auth/login")

        while not self.validate_login():
            time.sleep(5)
            logger.info(" Waiting for login...")

        logger.info(" Login detected! Proceeding with chat scraping.")

