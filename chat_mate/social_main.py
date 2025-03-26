#!/usr/bin/env python3
"""
Social Media Automation System
------------------------------
Unified CLI for managing social platform engagement across multiple services.
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("social/logs/social_main.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("social_main")

# Get the root directory path
file_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(file_dir) if os.path.basename(file_dir) == "social" else file_dir

# Ensure project root is in path
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Use the wrapper to get social_config
from social.social_config_wrapper import get_social_config
social_config = get_social_config()

# Create logs directory if it doesn't exist
logs_dir = os.path.join(root_dir, 'social', 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Add file logging
log_file = os.path.join(logs_dir, f"social_session_{datetime.now().strftime('%Y%m%d')}.log")
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(file_handler)

# Import configurations
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_driver(headless=False):
    """
    Initialize and return a Selenium WebDriver instance.
    """
    options = webdriver.ChromeOptions()
    profile_path = social_config.get_env("CHROME_PROFILE_PATH", os.path.join(os.getcwd(), "chrome_profile"))
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--start-maximized")
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")
    
    if headless:
        options.add_argument("--headless")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    logger.info(f"Chrome driver initialized with profile: {profile_path}")
    return driver

def load_platforms_config():
    """
    Load or create platform configurations from environment variables
    """
    config_path = os.path.join(root_dir, 'social', 'data', 'platform_config.json')
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    
    # Create default config from environment variables
    config = {
        'twitter': {
            'email': social_config.get_env('TWITTER_EMAIL'),
            'password': social_config.get_env('TWITTER_PASSWORD'),
            'api_key': social_config.get_env('TWITTER_API_KEY'),
            'api_secret': social_config.get_env('TWITTER_API_SECRET'),
            'access_token': social_config.get_env('TWITTER_ACCESS_TOKEN'),
            'access_token_secret': social_config.get_env('TWITTER_ACCESS_SECRET')
        },
        'instagram': {
            'email': social_config.get_env('INSTAGRAM_EMAIL'),
            'password': social_config.get_env('INSTAGRAM_PASSWORD'),
            'api_key': social_config.get_env('INSTAGRAM_API_KEY')
        },
        'facebook': {
            'email': social_config.get_env('FACEBOOK_EMAIL'),
            'password': social_config.get_env('FACEBOOK_PASSWORD'),
            'api_key': social_config.get_env('FACEBOOK_API_KEY')
        },
        'linkedin': {
            'email': social_config.get_env('LINKEDIN_EMAIL'),
            'password': social_config.get_env('LINKEDIN_PASSWORD'),
            'api_key': social_config.get_env('LINKEDIN_API_KEY')
        },
        'reddit': {
            'username': social_config.get_env('REDDIT_USERNAME'),
            'password': social_config.get_env('REDDIT_PASSWORD'),
            'client_id': social_config.get_env('REDDIT_CLIENT_ID'),
            'client_secret': social_config.get_env('REDDIT_CLIENT_SECRET')
        },
        'tiktok': {
            'email': social_config.get_env('TIKTOK_EMAIL'),
            'password': social_config.get_env('TIKTOK_PASSWORD')
        },
        'youtube': {
            'email': social_config.get_env('YOUTUBE_EMAIL'),
            'password': social_config.get_env('YOUTUBE_PASSWORD'),
            'api_key': social_config.get_env('YOUTUBE_API_KEY')
        }
    }
    
    # Save config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    
    return config

def run_social_engagement():
    """
    Main function to run social media engagement strategies.
    """
    logger.info("Starting Social Engagement Session...")
    
    # Load platform configurations
    platform_config = load_platforms_config()
    
    # Import strategy implementations
    from social.strategies.twitter_strategy import TwitterStrategy
    from social.strategies.instagram_strategy import InstagramStrategy
    from social.strategies.linkedin_strategy import LinkedinStrategy
    from social.strategies.facebook_strategy import FacebookStrategy
    from social.strategies.reddit_strategy import RedditStrategy
    from social.strategies.tiktok_strategy import TikTokStrategy
    from social.strategies.youtube_strategy import YouTubeStrategy
    
    # Map platforms to their strategy classes
    platforms = {
        'twitter': TwitterStrategy,
        'instagram': InstagramStrategy,
        'linkedin': LinkedinStrategy,
        'facebook': FacebookStrategy,
        'reddit': RedditStrategy,
        'tiktok': TikTokStrategy,
        'youtube': YouTubeStrategy
    }
    
    # Run sessions for each platform
    for platform_name, strategy_class in platforms.items():
        try:
            if platform_name not in platform_config:
                logger.warning(f"Missing configuration for {platform_name}. Skipping...")
                continue
                
            logger.info(f"Starting session for {platform_name}...")
            
            # Initialize the driver for each strategy
            driver = get_driver(headless=False)
            
            try:
                # Initialize the strategy with platform ID, config and driver
                strategy = strategy_class(
                    platform_id=platform_name,
                    config=platform_config.get(platform_name, {}),
                    driver=driver
                )
                
                # Run the daily session for this platform
                if hasattr(strategy, 'run_daily_session') and callable(getattr(strategy, 'run_daily_session')):
                    strategy.run_daily_session()
                else:
                    logger.warning(f"{platform_name} strategy does not have a run_daily_session method")
                
                logger.info(f"Completed session for {platform_name}")
            finally:
                # Make sure the driver is closed
                if driver:
                    driver.quit()
                    
        except Exception as e:
            logger.error(f"Error during {platform_name} session: {str(e)}", exc_info=True)
    
    logger.info("Social Engagement Session completed")

if __name__ == "__main__":
    run_social_engagement() 