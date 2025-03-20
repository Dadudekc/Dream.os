import os
import json
import logging
from jinja2 import Environment, FileSystemLoader

# Import individual platform strategies
from social.strategies.twitter_strategy import TwitterStrategy
from social.strategies.linkedin_strategy import LinkedInStrategy
from social.strategies.facebook_strategy import FacebookStrategy
from social.strategies.instagram_strategy import InstagramStrategy
from social.strategies.reddit_strategy import RedditStrategy
from social.strategies.stocktwits_strategy import StocktwitsStrategy

logger = logging.getLogger("AletheiaContentDispatcher")

class AletheiaContentDispatcher:
    def __init__(self, memory_update: dict, template_dir: str = "chat_mate/content/templates"):
        self.memory_update = memory_update
        self.env = Environment(loader=FileSystemLoader(template_dir))

        # Initialize platform strategies
        self.platforms = {
            "twitter": TwitterStrategy(self.env),
            "linkedin": LinkedInStrategy(self.env),
            "facebook": FacebookStrategy(self.env),
            "instagram": InstagramStrategy(self.env),
            "reddit": RedditStrategy(self.env),
            "stocktwits": StocktwitsStrategy(self.env)
        }

        logger.info("🚀 AletheiaContentDispatcher initialized with multi-platform strategies.")

    def execute_full_dispatch(self):
        logger.info("🚀 Dispatching content to all platforms...")
        
        # Iterate and post to each platform strategy
        for platform, strategy in self.platforms.items():
            try:
                logger.info(f"⚙️ Generating content for {platform.capitalize()}...")
                content = strategy.generate_content(self.memory_update)
                
                logger.info(f"📤 Dispatching to {platform.capitalize()}...")
                strategy.dispatch_content(content)
                
                logger.info(f"✅ {platform.capitalize()} post dispatched successfully.")
            except Exception as e:
                logger.error(f"❌ Failed to dispatch content to {platform.capitalize()}: {e}")

        logger.info("✅ All content dispatched via AletheiaContentDispatcher.")

# -----------------------------
# Example Usage
# -----------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    example_memory_update = {
        "project_milestones": ["Unified Social Authentication Rituals"],
        "newly_unlocked_protocols": ["Unified Social Logging Protocol (social_config)"],
        "quest_completions": ["Vanquished Complexity’s Whisper"],
        "feedback_loops_triggered": ["Social Media Auto-Dispatcher Loop"]
    }

    dispatcher = AletheiaContentDispatcher(memory_update=example_memory_update)
    dispatcher.execute_full_dispatch()
