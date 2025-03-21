import threading
from datetime import datetime

# Import the unified DriverManager
from core.DriverManager import DriverManager

# Import platform strategies
from social.strategies.twitter_strategy import TwitterStrategy
from social.strategies.facebook_strategy import FacebookStrategy
from social.strategies.instagram_strategy import InstagramStrategy
from social.strategies.reddit_strategy import RedditStrategy
from social.strategies.stocktwits_strategy import StocktwitsStrategy
from social.strategies.linkedin_strategy import LinkedinStrategy

# Import logging tools
from social.log_writer import logger, write_json_log


class SocialPostManager:
    """
    Manages posting of social media content across multiple platforms.
    Supports multi-threading for faster execution and centralized error handling.
    """

    def __init__(self, post_db, append_output=None):
        """
        Initialize the SocialPostManager with a post database and output callback.

        Args:
            post_db: An object responsible for managing post queue operations.
            append_output (callable, optional): Callback function for UI or console output. Defaults to print.
        """
        self.post_db = post_db
        self.append_output = append_output or print

        # Initialize unified DriverManager and share driver instance across platforms
        self.driver_manager = DriverManager(headless=False)  # Set to True if you want headless
        self.driver = self.driver_manager.get_driver()

        # Initialize platform strategies with the shared driver
        self.twitter_strategy = TwitterStrategy(driver=self.driver)
        self.facebook_strategy = FacebookStrategy(driver=self.driver)
        self.instagram_strategy = InstagramStrategy(driver=self.driver)
        self.reddit_strategy = RedditStrategy(driver=self.driver)
        self.stocktwits_strategy = StocktwitsStrategy(driver=self.driver)
        self.linkedin_strategy = LinkedinStrategy(driver=self.driver)

        logger.info("✅ SocialPostManager initialized with all platform strategies.")

    def post_next(self):
        """
        Retrieves the next post from the queue and dispatches it across all platforms concurrently.
        Uses threading to maximize speed.
        """
        post = self.post_db.get_next_post()
        if not post:
            self.append_output("🚫 No posts in queue.")
            return

        self.append_output(f"🚀 Posting: {post['title']}")

        failed_platforms = []

        def post_to_platform(platform_name, strategy_instance):
            """
            Worker function to post content to a single platform.

            Args:
                platform_name (str): Name of the social platform.
                strategy_instance (object): Instance of the platform's strategy class.
            """
            try:
                strategy_instance.post(post["content"])
                logger.info(f"✅ {platform_name} post successful.")
                write_json_log(platform_name, "successful", tags=["post"])
            except Exception as e:
                logger.error(f"❌ {platform_name} post failed: {e}")
                write_json_log(platform_name, "failed", tags=["post", "error"], ai_output=str(e))
                failed_platforms.append(platform_name)

        # Platform strategies mapped to their names
        post_tasks = {
            "Twitter": self.twitter_strategy,
            "Facebook": self.facebook_strategy,
            "Reddit": self.reddit_strategy,
            "Stocktwits": self.stocktwits_strategy,
            "LinkedIn": self.linkedin_strategy,
            "Instagram": self.instagram_strategy
        }

        # Create and start threads for concurrent posting
        threads = []
        for name, strategy in post_tasks.items():
            thread = threading.Thread(target=post_to_platform, args=(name, strategy))
            threads.append(thread)
            thread.start()
            logger.debug(f"🧵 Started thread for {name}")

        # Wait for all threads to finish
        for thread in threads:
            thread.join()
            logger.debug("🧵 Thread joined")

        # Final post status evaluation
        if failed_platforms:
            self.post_db.mark_failed(post)
            self.append_output(f"❌ Post failed on: {', '.join(failed_platforms)}")
        else:
            self.post_db.mark_posted(post)
            self.append_output(f"✅ Post completed successfully: {post['title']}")

    def post_all(self):
        """
        Processes the entire queue, posting all scheduled content across platforms.
        """
        while self.post_db.get_queue_length() > 0:
            self.post_next()

    def enqueue_post(self, title: str, content: str, tags: list = None):
        """
        Adds a new post to the queue.

        Args:
            title (str): Title of the post.
            content (str): Body/content of the post.
            tags (list, optional): List of tags associated with the post.
        """
        tags = tags or []
        post = {
            "title": title,
            "content": content,
            "tags": tags,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        self.post_db.add_to_queue(post)
        self.append_output(f"📥 Enqueued post: {title}")

    def shutdown(self):
        """
        Cleanly shuts down the driver manager.
        """
        self.driver_manager.quit_driver()
        logger.info("🔒 DriverManager shutdown complete.")
