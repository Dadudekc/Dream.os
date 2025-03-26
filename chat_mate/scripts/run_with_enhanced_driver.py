#!/usr/bin/env python3
"""
Run script for Chat_Mate application with the enhanced DriverManager.
This script tests the application startup with the new modular driver implementation.
"""

import os
import sys
import logging
import argparse

# Add the root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('chat_mate_run_test.log')
    ]
)
logger = logging.getLogger('run_test')

def main():
    """Run the application with the enhanced DriverManager."""
    parser = argparse.ArgumentParser(description='Run Chat_Mate with the enhanced DriverManager')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--model', default='gpt-4o', help='The ChatGPT model to use')
    parser.add_argument('--undetected', action='store_true', help='Use undetected mode')
    args = parser.parse_args()
    
    logger.info("Starting Chat_Mate with enhanced DriverManager")
    logger.info(f"Configuration: Headless={args.headless}, Model={args.model}, Undetected={args.undetected}")
    
    try:
        # Import DriverManager to ensure it can be loaded
        from core.chat_engine.driver_manager import DriverManager
        logger.info("Successfully imported enhanced DriverManager")
        
        # Initialize the DriverManager
        driver_manager = DriverManager(
            headless=args.headless,
            undetected_mode=args.undetected
        )
        logger.info("DriverManager initialized successfully")
        
        # Test the driver initialization
        driver = driver_manager.get_driver()
        if driver:
            logger.info("Driver initialized successfully")
            
            # Test navigation
            driver.get("https://chat.openai.com")
            logger.info(f"Successfully navigated to ChatGPT. Title: {driver.title}")
            
            # Test cookie management if cookie file is set
            if driver_manager.cookie_file:
                driver_manager.save_cookies()
                logger.info("Cookies saved successfully")
        else:
            logger.error("Failed to initialize driver")
            
        # Initialize ChatManager with the enhanced DriverManager
        from core.ChatManager import ChatManager
        
        # Create a simple config object
        class Config:
            def __init__(self):
                self.headless = args.headless
                self.default_model = args.model
                self.excluded_chats = []
                
            def get(self, key, default=None):
                return getattr(self, key, default)
        
        config = Config()
        chat_manager = ChatManager(config, logger)
        logger.info("ChatManager initialized successfully")
        
        # Test startup
        chat_manager.start()
        logger.info("ChatManager started successfully")
        
        # Cleanup
        chat_manager.shutdown_driver()
        logger.info("ChatManager shutdown successfully")
        
        logger.info("All tests passed! The enhanced DriverManager is working correctly.")
        return 0
        
    except Exception as e:
        logger.exception(f"Error during test: {e}")
        return 1
        
if __name__ == "__main__":
    sys.exit(main()) 