import time
import random
import json
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    TimeoutException
)

from utils.cookie_manager import CookieManager
from social.log_writer import logger, write_json_log
from social.social_config import social_config
from utils.SentimentAnalyzer import SentimentAnalyzer
from social.AIChatAgent import AIChatAgent

PLATFORM = "reddit"
LOGIN_URL = "https://www.reddit.com/login/"
SOCIAL_CREDENTIALS = {
    "username": social_config.get_env("REDDIT_USERNAME"),
    "password": social_config.get_env("REDDIT_PASSWORD")
}

class RedditCommunityArchitect:
    """
    Reddit Engagement Bot: Automates Reddit community building through
    AI-generated posts, comments, and upvotes in Victor's authentic voice.
    """

    FOLLOW_DB = "social/data/reddit_follow_tracker.json"

    def __init__(self, driver):
        self.driver = driver
        self.cookie_manager = CookieManager()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.ai_agent = AIChatAgent(model="gpt-4o", tone="Victor", provider="openai")

    # ===================================
    # Login
    # ===================================
    def login(self):
        logger.info("🌐 Reddit login initiated...")
        self.driver.get(LOGIN_URL)
        self.cookie_manager.load_cookies(self.driver, PLATFORM)
        self.driver.refresh()
        time.sleep(random.uniform(3, 5))

        if "login" not in self.driver.current_url:
            logger.info("✅ Logged into Reddit via cookies.")
            return True

        # Auto-login fallback
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "loginUsername"))
            ).send_keys(SOCIAL_CREDENTIALS["username"])

            self.driver.find_element(By.ID, "loginPassword").send_keys(
                SOCIAL_CREDENTIALS["password"], Keys.RETURN)

            WebDriverWait(self.driver, 10).until(
                lambda d: "login" not in d.current_url
            )

            logger.info("✅ Auto-login successful.")
            self.cookie_manager.save_cookies(self.driver, PLATFORM)
            return True

        except Exception as e:
            logger.warning(f"⚠️ Auto-login failed: {e}")

        # Manual login
        return self.cookie_manager.wait_for_manual_login(
            self.driver,
            lambda d: "login" not in d.current_url,
            PLATFORM
        )

    # ===================================
    # Post Creation
    # ===================================
    def post(self, subreddit, title_prompt, body_prompt):
        """
        Submit a Reddit post (title + body), AI-generated in Victor's voice.
        """
        submit_url = f"https://www.reddit.com/r/{subreddit}/submit"
        logger.info(f"🚀 Navigating to {submit_url}")
        self.driver.get(submit_url)

        # AI-Generated content
        title = self.ai_agent.ask(title_prompt) or title_prompt
        body = self.ai_agent.ask(body_prompt) or body_prompt

        try:
            # Fill title
            title_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[name='title']"))
            )
            title_field.clear()
            title_field.send_keys(title)
            time.sleep(random.uniform(1, 2))

            # Fill body (optional)
            body_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='post-content'] div[role='textbox']"))
            )
            body_field.click()
            time.sleep(random.uniform(1, 2))
            body_field.send_keys(body)
            time.sleep(random.uniform(1, 2))

            # Submit
            post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Post')]"))
            )
            post_button.click()

            logger.info(f"✅ Successfully posted to r/{subreddit}.")
            write_json_log(PLATFORM, "success", f"Posted to r/{subreddit}")
            time.sleep(random.uniform(3, 5))
            return True

        except Exception as e:
            logger.error(f"❌ Post to r/{subreddit} failed: {e}")
            write_json_log(PLATFORM, "failed", f"Posting error: {e}")
            return False

    # ===================================
    # Community Engagement
    # ===================================
    def engage_community(self, subreddit, interactions=5, comment_probability=0.6):
        """
        Engage with Reddit posts by upvoting, commenting, and tracking sentiment.
        """
        logger.info(f"🚀 Engaging with r/{subreddit} community...")
        self.driver.get(f"https://www.reddit.com/r/{subreddit}/new/")
        time.sleep(random.uniform(2, 4))

        posts = self.driver.find_elements(By.CSS_SELECTOR, "article")
        random.shuffle(posts)

        for post in posts[:interactions]:
            try:
                # Upvote
                upvote_btn = post.find_element(By.XPATH, ".//button[@aria-label='upvote']")
                upvote_btn.click()
                logger.info("⬆️ Upvoted a post.")
                time.sleep(random.uniform(1, 2))

                # Sentiment Analysis for feedback loop
                post_text = post.text
                sentiment = self.sentiment_analyzer.analyze(post_text)
                logger.debug(f"🧠 Sentiment score: {sentiment}")

                # Conditional Comment
                if random.random() < comment_probability:
                    self.comment_on_post(post)

            except Exception as e:
                logger.warning(f"⚠️ Engagement error: {e}")

    def comment_on_post(self, post_element):
        """
        Leave an AI-generated comment on a post in Victor's authentic voice.
        """
        try:
            comment_link = post_element.find_element(By.CSS_SELECTOR, "a[data-click-id='comments']")
            self.driver.execute_script("arguments[0].click();", comment_link)
            time.sleep(random.uniform(2, 3))

            comment_box = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[role='textbox']"))
            )

            comment_prompt = (
                "Write a short, engaging comment that adds value to the discussion, "
                "in my authentic voice. Stay aligned with strategic growth and AI systems."
            )

            comment = self.ai_agent.ask(
                prompt=comment_prompt,
                additional_context=post_element.text,
                metadata={"platform": "Reddit", "persona": "Victor"}
            )

            comment_box.click()
            comment_box.send_keys(comment)
            comment_box.send_keys(Keys.CONTROL, Keys.RETURN)

            logger.info(f"💬 Comment posted: {comment}")
            time.sleep(random.uniform(2, 3))
            self.driver.back()

        except Exception as e:
            logger.warning(f"⚠️ Commenting error: {e}")

    # ===================================
    # Subreddit Subscription (Analogous to follow)
    # ===================================
    def subscribe_to_subreddit(self, subreddit):
        """
        Subscribe to a subreddit (acts as 'follow' in Reddit ecosystem).
        """
        logger.info(f"🚀 Subscribing to r/{subreddit}...")
        subreddit_url = f"https://www.reddit.com/r/{subreddit}/"
        self.driver.get(subreddit_url)
        time.sleep(random.uniform(2, 4))

        try:
            join_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Join')]"))
            )
            join_btn.click()

            logger.info(f"✅ Subscribed to r/{subreddit}.")
            self._log_subscription(subreddit)

        except Exception as e:
            logger.warning(f"⚠️ Failed to subscribe to r/{subreddit}: {e}")

    def unsubscribe_from_subreddit(self, subreddit):
        """
        Unsubscribe from a subreddit.
        """
        logger.info(f"🚀 Unsubscribing from r/{subreddit}...")
        subreddit_url = f"https://www.reddit.com/r/{subreddit}/"
        self.driver.get(subreddit_url)
        time.sleep(random.uniform(2, 4))

        try:
            joined_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Joined')]"))
            )
            joined_btn.click()

            logger.info(f"➖ Unsubscribed from r/{subreddit}.")
            self._remove_subscription(subreddit)

        except Exception as e:
            logger.warning(f"⚠️ Failed to unsubscribe from r/{subreddit}: {e}")

    def _log_subscription(self, subreddit):
        if not subreddit:
            return
        if not os.path.exists(self.FOLLOW_DB):
            subscriptions = {}
        else:
            with open(self.FOLLOW_DB, "r") as f:
                subscriptions = json.load(f)

        subscriptions[subreddit] = {
            "subscribed_at": datetime.utcnow().isoformat(),
            "status": "subscribed"
        }

        with open(self.FOLLOW_DB, "w") as f:
            json.dump(subscriptions, f, indent=4)

    def _remove_subscription(self, subreddit):
        if not os.path.exists(self.FOLLOW_DB):
            return
        with open(self.FOLLOW_DB, "r") as f:
            subscriptions = json.load(f)

        if subreddit in subscriptions:
            subscriptions[subreddit]["status"] = "unsubscribed"

        with open(self.FOLLOW_DB, "w") as f:
            json.dump(subscriptions, f, indent=4)

    # ===================================
    # Viral Engagement
    # ===================================
    def viral_engagement(self, subreddit):
        logger.info(f"🚀 Running viral engagement on r/{subreddit}...")
        self.driver.get(f"https://www.reddit.com/r/{subreddit}/top/?t=day")
        time.sleep(random.uniform(2, 4))

        posts = self.driver.find_elements(By.CSS_SELECTOR, "article")
        for post in posts[:3]:
            try:
                upvote_btn = post.find_element(By.XPATH, ".//button[@aria-label='upvote']")
                upvote_btn.click()

                comment = self.ai_agent.ask(
                    prompt="Compose a viral comment that sparks discussion about system convergence and trading mastery.",
                    additional_context=post.text,
                    metadata={"platform": "Reddit", "persona": "Victor"}
                )

                comment_link = post.find_element(By.CSS_SELECTOR, "a[data-click-id='comments']")
                self.driver.execute_script("arguments[0].click();", comment_link)
                time.sleep(random.uniform(2, 3))

                comment_box = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div[role='textbox']"))
                )
                comment_box.send_keys(comment)
                comment_box.send_keys(Keys.CONTROL, Keys.RETURN)

                logger.info(f"🔥 Viral comment posted: {comment}")
                time.sleep(random.uniform(2, 3))
                self.driver.back()

            except Exception as e:
                logger.warning(f"⚠️ Viral engagement failed: {e}")

    # ===================================
    # Daily Session Runner
    # ===================================
    def run_daily_session(self, subreddit, post_prompts=None):
        logger.info("🚀 Starting Reddit Daily Community Session...")

        if not self.login():
            logger.error("❌ Login failed. Aborting session.")
            return

        # Post if prompts provided
        if post_prompts:
            self.post(subreddit, *post_prompts)

        # Community Engagement
        self.engage_community(subreddit=subreddit, interactions=5, comment_probability=0.7)

        # Viral Engagement
        self.viral_engagement(subreddit=subreddit)

        logger.info("✅ Reddit Daily Session Complete.")

# ===================================
# Unified Reddit Strategy Class
# ===================================
class RedditStrategy(RedditCommunityArchitect):
    """
    Centralized strategy class for Reddit automation and community building.
    Extends RedditCommunityArchitect with:
      - Dynamic feedback loops (engagement metrics analysis).
      - AI sentiment analysis & reinforcement loops.
      - Reward system for top engagers.
      - Cross-platform feedback integration.
    """
    FEEDBACK_DB = "social/data/reddit_feedback_tracker.json"
    REWARD_DB = "social/data/reddit_reward_tracker.json"

    def __init__(self, driver):
        super().__init__(driver)
        self.feedback_data = self._load_feedback_data()

    def _load_feedback_data(self):
        if os.path.exists(self.FEEDBACK_DB):
            with open(self.FEEDBACK_DB, "r") as f:
                return json.load(f)
        return {}

    def _save_feedback_data(self):
        with open(self.FEEDBACK_DB, "w") as f:
            json.dump(self.feedback_data, f, indent=4)

    def analyze_engagement_metrics(self):
        """
        Analyze and update engagement metrics.
        (For demo, metrics are incremented randomly.)
        """
        logger.info("📊 Analyzing Reddit engagement metrics...")
        self.feedback_data["upvotes"] = self.feedback_data.get("upvotes", 0) + random.randint(5, 10)
        self.feedback_data["comments"] = self.feedback_data.get("comments", 0) + random.randint(2, 5)
        self.feedback_data["subscriptions"] = self.feedback_data.get("subscriptions", 0) + random.randint(1, 3)
        logger.info(f"👍 Upvotes: {self.feedback_data['upvotes']}, 💬 Comments: {self.feedback_data['comments']}, ➕ Subscriptions: {self.feedback_data['subscriptions']}")
        self._save_feedback_data()

    def adaptive_posting_strategy(self):
        """
        Adjust posting strategy based on engagement feedback.
        """
        logger.info("🔄 Adapting Reddit posting strategy based on feedback...")
        if self.feedback_data.get("upvotes", 0) > 100:
            logger.info("🔥 High engagement detected! Consider increasing post frequency.")
        if self.feedback_data.get("comments", 0) > 50:
            logger.info("💡 More discussion-oriented posts may yield better community interaction.")

    def analyze_comment_sentiment(self, comment):
        """
        Analyze sentiment of a comment using AI.
        Returns 'positive', 'neutral', or 'negative'.
        """
        sentiment_prompt = f"Analyze the sentiment of the following comment: '{comment}'. Respond with positive, neutral, or negative."
        sentiment = self.ai_agent.ask(prompt=sentiment_prompt, metadata={"platform": "Reddit", "persona": "Victor"})
        sentiment = sentiment.strip().lower() if sentiment else "neutral"
        logger.info(f"Sentiment for comment '{comment}': {sentiment}")
        return sentiment

    def reinforce_engagement(self, comment):
        """
        If a comment is positive, generate a reinforcement response in my voice.
        """
        sentiment = self.analyze_comment_sentiment(comment)
        if sentiment == "positive":
            reinforcement_prompt = f"As Victor, write an engaging response to: '{comment}' to further boost community spirit."
            response = self.ai_agent.ask(prompt=reinforcement_prompt, metadata={"platform": "Reddit", "persona": "Victor"})
            logger.info(f"Reinforcement response generated: {response}")
            # Optionally, automate replying to the comment.
            return response
        return None

    def reward_top_engagers(self):
        """
        Reward top community engagers with custom shout-outs.
        """
        logger.info("🎉 Evaluating top engagers for rewards on Reddit...")
        if os.path.exists(self.REWARD_DB):
            with open(self.REWARD_DB, "r") as f:
                reward_data = json.load(f)
        else:
            reward_data = {}

        # Stub: For demo, randomly select a subreddit from subscriptions in FOLLOW_DB
        if os.path.exists(self.FOLLOW_DB):
            with open(self.FOLLOW_DB, "r") as f:
                subscription_data = json.load(f)
            top_subreddit = max(subscription_data.items(), key=lambda x: random.random(), default=(None, None))[0]
            if top_subreddit and top_subreddit not in reward_data:
                custom_message = f"Hey r/{top_subreddit}, your engagement is phenomenal! Thanks for driving our community growth."
                reward_data[top_subreddit] = {"rewarded_at": datetime.utcnow().isoformat(), "message": custom_message}
                logger.info(f"Reward issued to subreddit: r/{top_subreddit}")
                write_json_log(PLATFORM, "success", tags=["reward"], ai_output=top_subreddit)
        else:
            logger.warning("No subscription data available for rewards on Reddit.")

        with open(self.REWARD_DB, "w") as f:
            json.dump(reward_data, f, indent=4)

    def cross_platform_feedback_loop(self):
        """
        Merge Reddit engagement with data from other platforms (stub).
        """
        logger.info("🌐 Merging cross-platform feedback loops for Reddit...")
        twitter_data = {"upvotes": random.randint(8, 15), "comments": random.randint(3, 8)}
        facebook_data = {"upvotes": random.randint(10, 20), "comments": random.randint(5, 10)}
        unified_metrics = {
            "reddit": self.feedback_data,
            "twitter": twitter_data,
            "facebook": facebook_data
        }
        logger.info(f"Unified Metrics: {unified_metrics}")

    def run_feedback_loop(self):
        self.analyze_engagement_metrics()
        self.adaptive_posting_strategy()

    def run_daily_strategy_session(self, subreddit, post_prompts=None):
        """
        Full daily strategy session:
          - Run standard community session.
          - Process feedback, analyze sentiment, reinforce engagement.
          - Reward top engagers.
          - Merge cross-platform data.
        """
        logger.info("🚀 Starting Full Reddit Strategy Session.")
        self.run_daily_session(subreddit, post_prompts)

        # Process sample comments for reinforcement
        sample_comments = [
            "This is incredible!",
            "Not impressed by this post.",
            "I love the authentic vibe here."
        ]
        for comment in sample_comments:
            self.reinforce_engagement(comment)

        self.run_feedback_loop()
        self.reward_top_engagers()
        self.cross_platform_feedback_loop()
        logger.info("✅ Reddit Strategy Session Complete.")

# ===================================
# Autonomous Execution Example
# ===================================
if __name__ == "__main__":
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    reddit_strategy = RedditStrategy(driver)
    
    subreddit = "community_engagement"
    post_prompts = [
        "Compose a Reddit post title that highlights my system convergence philosophy.",
        "Write a Reddit post body explaining how AI and trading mastery create exponential growth loops."
    ]

    reddit_strategy.run_daily_strategy_session(subreddit, post_prompts)
    driver.quit()
