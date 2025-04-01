import threading
import time
from typing import List, Dict, Any
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from .utils import logger, RATE_LIMIT_DELAY, MAX_ACTIONS_BEFORE_COOLDOWN, COOLDOWN_PERIOD

class ConversationScraper:
    """Manages conversation scraping and processing."""
    
    def __init__(self, chat_manager, response_handler, narrative_manager, memory_manager):
        """
        Initialize the conversation scraper.
        
        Args:
            chat_manager: ChatManager instance for accessing conversations
            response_handler: ResponseHandler instance for processing responses
            narrative_manager: NarrativeManager instance for processing narrative elements
            memory_manager: MemoryManager instance for storing results
        """
        self.chat_manager = chat_manager
        self.response_handler = response_handler
        self.narrative_manager = narrative_manager
        self.memory_manager = memory_manager
        self.action_count = 0
        self.last_action_time = time.time()
    
    def scrape_conversations(self, prompts: List[str], cycle_speed: int = 2) -> None:
        """
        Start scraping conversations in a separate thread.
        
        Args:
            prompts: List of prompts to use
            cycle_speed: Delay between prompts
        """
        thread = threading.Thread(
            target=self._scrape_thread,
            args=(prompts, cycle_speed),
            daemon=True
        )
        thread.start()
    
    def _scrape_thread(self, prompts: List[str], cycle_speed: int) -> None:
        """
        Main scraping thread that processes conversations.
        
        Args:
            prompts: List of prompts to use
            cycle_speed: Delay between prompts
        """
        logger.info(f"Starting conversation scraping with {len(prompts)} prompts")
        
        if not self.response_handler.is_logged_in():
            self._manual_login()
        
        # Get all available conversations
        all_chats = self.chat_manager.get_all_chat_titles()
        if not all_chats:
            logger.warning("No conversations found to scrape")
            return
        
        for chat in all_chats:
            chat_title = chat.get("title", "Untitled")
            logger.info(f"\n=== Processing Chat: {chat_title} ===")
            
            # Navigate to chat
            self.response_handler.driver.get(chat.get("link"))
            self._wait_for_page_load(self.response_handler.driver)
            
            # Process each prompt
            for prompt_type in prompts:
                try:
                    # Get context-aware prompt
                    prompt_text = self._get_contextual_prompt(prompt_type)
                    
                    # Send prompt and get response
                    if not self.response_handler.send_prompt(prompt_text):
                        logger.error(f"Failed to send prompt '{prompt_type}' to {chat_title}")
                        continue
                    
                    response = self.response_handler.wait_for_stable_response()
                    if not response:
                        logger.warning(f"No response received for prompt '{prompt_type}' in {chat_title}")
                        continue
                    
                    # Process response
                    feedback = self.narrative_manager.process_response(
                        prompt_type=prompt_type,
                        prompt_text=prompt_text,
                        response=response,
                        chat_title=chat_title
                    )
                    
                    # Update memory
                    narrative_data = self.narrative_manager.extract_narrative_elements(response)
                    self.memory_manager.update(feedback, narrative_data, self.narrative_manager.system_state.get_state())
                    
                    # Rate limiting
                    self._handle_rate_limiting()
                    time.sleep(cycle_speed)
                    
                except Exception as e:
                    logger.error(f"Error processing prompt '{prompt_type}' in {chat_title}: {e}")
                    continue
    
    def _get_contextual_prompt(self, prompt_type: str) -> str:
        """
        Get a context-aware prompt.
        
        Args:
            prompt_type: Type of prompt to get
            
        Returns:
            Contextualized prompt text
        """
        try:
            # Get base prompt
            base_prompt = self.chat_manager.prompt_manager.get_prompt(prompt_type)
            
            # Add system state context
            context = self.narrative_manager.system_state.get_state()
            
            # Render prompt with context
            from jinja2 import Template
            template = Template(base_prompt)
            return template.render(**context)
            
        except Exception as e:
            logger.error(f"Failed to get contextual prompt: {e}")
            return ""
    
    def _manual_login(self) -> None:
        """Handle manual login process."""
        try:
            self.response_handler.driver.get(self.response_handler.login_url)
            self._wait_for_page_load(self.response_handler.driver)
            
            # Wait for user to log in manually
            logger.info("Please log in manually in the browser window...")
            WebDriverWait(self.response_handler.driver, 300).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='chat-list']"))
            )
            
            logger.info("Login successful")
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise
    
    def _wait_for_page_load(self, driver, timeout: int = 10) -> None:
        """
        Wait for page to load completely.
        
        Args:
            driver: WebDriver instance
            timeout: Maximum time to wait
        """
        try:
            WebDriverWait(driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
        except Exception as e:
            logger.warning(f"Page load wait timed out: {e}")
    
    def _handle_rate_limiting(self) -> None:
        """Handle rate limiting logic."""
        current_time = time.time()
        
        # Check if we need to apply rate limiting
        if current_time - self.last_action_time < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY)
        
        self.action_count += 1
        self.last_action_time = current_time
        
        # Check if we need to enter cooldown period
        if self.action_count >= MAX_ACTIONS_BEFORE_COOLDOWN:
            logger.info(f"Entering cooldown period for {COOLDOWN_PERIOD} seconds")
            time.sleep(COOLDOWN_PERIOD)
            self.action_count = 0 
