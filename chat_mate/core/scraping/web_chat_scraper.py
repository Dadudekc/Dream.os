#!/usr/bin/env python3
"""
WebChatScraper
-------------

This module provides functionality to scrape chat data directly from the ChatGPT web interface.
It is designed to work with the existing Dream.OS architecture, specifically with the DriverManager.

Features:
- Scrape list of available chats
- Scrape complete message history from a specific chat
- Handle pagination and dynamic content loading
"""

import time
import logging
import re
import os
from typing import List, Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebChatScraper")

class WebChatScraper:
    """
    WebChatScraper extracts chat data directly from the ChatGPT web interface.
    It uses Selenium to navigate the DOM and extract chat titles and message content.
    """
    
    # Constants
    CHAT_BASE_URL = "https://chat.openai.com/"
    WAIT_TIMEOUT = 10
    CHAT_LINK_XPATH = "//a[contains(@class, 'group') and contains(@href, '/c/')]"
    CHAT_TITLE_SELECTOR = "h1.text-xl"
    USER_MESSAGE_SELECTOR = "div[data-message-author-role='user']"
    ASSISTANT_MESSAGE_SELECTOR = "div[data-message-author-role='assistant']"
    LOAD_MORE_BUTTON_SELECTOR = "button.btn-neutral:has-text('Show more')"
    
    def __init__(self, driver_manager, logger=None, excluded_chats=None):
        """
        Initialize WebChatScraper.
        
        Args:
            driver_manager: The driver manager instance
            logger: Optional logger instance
            excluded_chats: List of chat titles to exclude
        """
        self.driver_manager = driver_manager
        self.logger = logger or logging.getLogger(__name__)
        self.excluded_chats = excluded_chats or []
        
    def get_driver(self):
        """Get the driver instance, initializing it if needed."""
        if hasattr(self.driver_manager, 'get_driver'):
            return self.driver_manager.get_driver()
        else:
            # Fallback to direct driver property
            return getattr(self.driver_manager, 'driver', None)
            
    def navigate_to_chatgpt(self):
        """Navigate to the ChatGPT homepage and wait for it to load."""
        driver = self.get_driver()
        if not driver:
            self.logger.error("Driver not initialized")
            return False
            
        try:
            driver.get(self.CHAT_BASE_URL)
            WebDriverWait(driver, self.WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, "//nav[contains(@class, 'flex h-full')]"))
            )
            return True
        except Exception as e:
            self.logger.error(f"Error navigating to ChatGPT: {e}")
            return False
            
    def scrape_chat_list(self) -> List[Dict[str, str]]:
        """
        Scrape the list of available chats from the sidebar.
        
        Returns:
            List of chat dictionaries with 'title' and 'link'
        """
        self.logger.info("Scraping chat list from ChatGPT sidebar")
        if not self.navigate_to_chatgpt():
            return []
            
        driver = self.get_driver()
        try:
            # Wait for chats to load in sidebar
            WebDriverWait(driver, self.WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, self.CHAT_LINK_XPATH))
            )
            
            # Find all chat elements
            chat_elements = driver.find_elements(By.XPATH, self.CHAT_LINK_XPATH)
            if not chat_elements:
                self.logger.warning("No chats found in sidebar")
                return []
                
            # Extract title and link data
            chats = []
            for element in chat_elements:
                try:
                    title = element.text.strip()
                    if not title:
                        continue
                        
                    # Skip excluded chats
                    if title in self.excluded_chats:
                        self.logger.info(f"Skipping excluded chat: {title}")
                        continue
                        
                    link = element.get_attribute("href")
                    chats.append({"title": title, "link": link})
                except StaleElementReferenceException:
                    self.logger.warning("Element became stale during scraping")
                    continue
                    
            self.logger.info(f"Found {len(chats)} chats in sidebar")
            return chats
            
        except Exception as e:
            self.logger.error(f"Error scraping chat list: {e}")
            return []
            
    def navigate_to_chat(self, chat_title: str) -> bool:
        """
        Navigate to a specific chat by title.
        
        Args:
            chat_title: The title of the chat to navigate to
            
        Returns:
            True if navigation successful, False otherwise
        """
        self.logger.info(f"Navigating to chat: {chat_title}")
        driver = self.get_driver()
        
        # First get the chat list
        chats = self.scrape_chat_list()
        if not chats:
            self.logger.error("No chats found")
            return False
            
        # Find the chat with the matching title
        target_chat = next((chat for chat in chats if chat["title"] == chat_title), None)
        if not target_chat:
            self.logger.error(f"Chat with title '{chat_title}' not found")
            return False
            
        # Navigate to the chat link
        try:
            driver.get(target_chat["link"])
            WebDriverWait(driver, self.WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.CHAT_TITLE_SELECTOR))
            )
            return True
        except Exception as e:
            self.logger.error(f"Error navigating to chat '{chat_title}': {e}")
            return False
            
    def load_all_chat_messages(self):
        """
        Load all messages in the chat by repeatedly clicking 'Show more' 
        until all messages are loaded.
        """
        driver = self.get_driver()
        max_attempts = 10
        attempts = 0
        
        try:
            while attempts < max_attempts:
                try:
                    # Find load more button
                    load_more_button = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-neutral"))
                    )
                    
                    # Check if button text contains "Show more"
                    if "Show more" in load_more_button.text:
                        self.logger.info("Clicking 'Show more' button")
                        load_more_button.click()
                        time.sleep(1)  # Wait for messages to load
                        attempts += 1
                    else:
                        # If button exists but not "Show more", break
                        break
                except TimeoutException:
                    # No load more button found
                    self.logger.info("No more 'Show more' buttons found")
                    break
                    
            self.logger.info("All messages loaded")
            return True
        except Exception as e:
            self.logger.error(f"Error loading chat messages: {e}")
            return False
            
    def extract_message_content(self, message_element) -> Dict[str, Any]:
        """
        Extract content and metadata from a message element.
        
        Args:
            message_element: The Selenium element for the message
            
        Returns:
            Dictionary with message content and metadata
        """
        try:
            # Get the role (user or assistant)
            role = message_element.get_attribute("data-message-author-role")
            
            # Get the content div
            content_div = message_element.find_element(By.CSS_SELECTOR, ".markdown")
            content = content_div.text
            
            # Get timestamp if available
            timestamp = None
            try:
                timestamp_element = message_element.find_element(By.CSS_SELECTOR, "time")
                timestamp = timestamp_element.get_attribute("datetime")
            except NoSuchElementException:
                pass
                
            return {
                "role": role,
                "content": content,
                "timestamp": timestamp
            }
        except Exception as e:
            self.logger.error(f"Error extracting message content: {e}")
            return {"role": "unknown", "content": "", "timestamp": None}
            
    def scrape_chat_by_title(self, chat_title: str) -> List[Dict[str, Any]]:
        """
        Scrape the full chat history for a specific chat by title.
        
        Args:
            chat_title: The title of the chat to scrape
            
        Returns:
            List of message dictionaries
        """
        self.logger.info(f"Scraping chat history for: {chat_title}")
        
        # Navigate to the chat
        if not self.navigate_to_chat(chat_title):
            return []
            
        # Load all messages
        if not self.load_all_chat_messages():
            self.logger.warning("Could not load all messages, proceeding with visible ones")
            
        # Extract messages
        driver = self.get_driver()
        try:
            # Find all user and assistant messages
            user_messages = driver.find_elements(By.CSS_SELECTOR, self.USER_MESSAGE_SELECTOR)
            assistant_messages = driver.find_elements(By.CSS_SELECTOR, self.ASSISTANT_MESSAGE_SELECTOR)
            
            # Sort messages based on position in DOM
            all_messages_elements = user_messages + assistant_messages
            all_messages_elements.sort(key=lambda el: el.location['y'])
            
            # Extract content from each message
            messages = []
            for message_element in all_messages_elements:
                message_data = self.extract_message_content(message_element)
                messages.append(message_data)
                
            self.logger.info(f"Extracted {len(messages)} messages from chat")
            return messages
            
        except Exception as e:
            self.logger.error(f"Error scraping chat '{chat_title}': {e}")
            return [] 
