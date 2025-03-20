import time
import os
import random
import json
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException, ElementClickInterceptedException, TimeoutException
)

from utils.cookie_manager import CookieManager
from social.log_writer import write_json_log, logger
from social.social_config import social_config
from social.AIChatAgent import AIChatAgent
from utils.SentimentAnalyzer import SentimentAnalyzer

PLATFORM = "stocktwits"
FOLLOW_DB = "social/data/stocktwits_follow_tracker.json"

LOGIN_WAIT_TIME = 5
POST_WAIT_TIME = 3
RETRY_DELAY = 2
MAX_RETRIES = 3
ENGAGE_WAIT_TIME = 3

class StocktwitsCommunityArchitect:
    """
    Stocktwits Community Builder:
    Automates posts, engagement, and follower interactions with AI-generated content in Victor's authentic tone.
    """
    def __init__(self, driver):
        self.driver = driver
        self.cookie_manager = CookieManager()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.ai_agent = AIChatAgent(model="gpt-4o", tone="Victor", provider="openai")

    # ===================================
    # LOGIN
    # ===================================
    def login(self):
        logger.info(f"🚀 Logging in to {PLATFORM}")
        login_url = social_config.get_platform_url(PLATFORM, "login")
        self.driver.get(login_url)
        time.sleep(3)
        self.cookie_manager.load_cookies(self.driver, PLATFORM)
        self.driver.refresh()
        time.sleep(3)
        if self.is_logged_in():
            logger.info(f"✅ Logged into {PLATFORM} via cookies.")
            write_json_log(PLATFORM, "success", tags=["login", "cookie"])
            return True

        username = social_config.get_env("STOCKTWITS_USERNAME")
        password = social_config.get_env("STOCKTWITS_PASSWORD")

        try:
            username_field = self.driver.find_element(By.NAME, "username")
            password_field = self.driver.find_element(By.NAME, "password")
            login_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Log In')]")

            username_field.clear()
            username_field.send_keys(username)
            time.sleep(1)

            password_field.clear()
            password_field.send_keys(password)
            time.sleep(1)

            login_button.click()
            time.sleep(LOGIN_WAIT_TIME)
        except Exception as e:
            logger.warning(f"⚠️ Auto-login failed: {e}")
            write_json_log(PLATFORM, "failed", tags=["login", "auto"], ai_output=str(e))

        if not self.is_logged_in():
            logger.warning(f"⚠️ Manual login fallback initiated for {PLATFORM}")
            self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, PLATFORM)

        if self.is_logged_in():
            self.cookie_manager.save_cookies(self.driver, PLATFORM)
            logger.info(f"✅ Login successful for {PLATFORM}")
            write_json_log(PLATFORM, "success", tags=["login"])
            return True
        else:
            logger.error(f"❌ Login failed for {PLATFORM}")
            write_json_log(PLATFORM, "failed", tags=["login"])
            return False

    def is_logged_in(self):
        settings_url = social_config.get_platform_url(PLATFORM, "settings")
        self.driver.get(settings_url)
        time.sleep(3)
        logged_in = "settings" in self.driver.current_url
        logger.info(f"🔎 Login status on {PLATFORM}: {'✅ Logged in' if logged_in else '❌ Not logged in'}")
        return logged_in

    # ===================================
    # POSTING
    # ===================================
    def post(self, content, retries=MAX_RETRIES):
        logger.info(f"📝 Preparing to post to {PLATFORM}")
        if not self.is_logged_in():
            logger.warning("⚠️ Cannot post—user not logged in")
            return False

        post_url = social_config.get_platform_url(PLATFORM, "post")
        for attempt in range(1, retries + 1):
            try:
                self.driver.get(post_url)
                time.sleep(POST_WAIT_TIME)
                post_field = self.driver.find_element(By.ID, "message")
                post_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Post')]")
                post_field.clear()
                post_field.send_keys(content)
                time.sleep(1)
                post_button.click()
                logger.info(f"✅ Post published on {PLATFORM}")
                write_json_log(PLATFORM, "success", tags=["post"], ai_output=f"{content[:50]}...")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Attempt {attempt} failed: {e}")
                time.sleep(RETRY_DELAY)
        logger.error(f"❌ Failed to post on {PLATFORM} after {retries} attempts")
        write_json_log(PLATFORM, "failed", tags=["post"])
        return False

    # ===================================
    # COMMUNITY ENGAGEMENT
    # ===================================
    def engage_community(self, viral_prompt, interactions=5):
        logger.info(f"🚀 Engaging community on {PLATFORM}")
        trending_url = social_config.get_platform_url(PLATFORM, "trending")
        self.driver.get(trending_url)
        time.sleep(ENGAGE_WAIT_TIME)
        posts = self.driver.find_elements(By.CSS_SELECTOR, "article")
        if not posts:
            logger.warning(f"⚠️ No posts found on {PLATFORM}")
            return
        random.shuffle(posts)
        selected_posts = posts[:interactions]
        for post in selected_posts:
            try:
                # Upvote
                upvote_button = post.find_element(By.XPATH, ".//button[contains(@aria-label, 'upvote')]")
                upvote_button.click()
                logger.info("⬆️ Upvoted a post.")
                time.sleep(1)
                # Comment using AI
                post_text = post.text
                comment = self.ai_agent.ask(
                    prompt=viral_prompt,
                    additional_context=post_text,
                    metadata={"platform": PLATFORM, "persona": "Victor", "engagement": "viral"}
                )
                comment_button = post.find_element(By.XPATH, ".//button[contains(@aria-label, 'comment')]")
                comment_button.click()
                time.sleep(2)
                comment_field = self.driver.find_element(By.XPATH, "//textarea[@placeholder='Add a comment']")
                comment_field.send_keys(comment)
                comment_field.send_keys(Keys.CONTROL, Keys.RETURN)
                logger.info(f"💬 Comment posted: {comment}")
                # Optional: Attempt follow (if available)
                try:
                    follow_button = post.find_element(By.XPATH, ".//button[contains(text(), 'Follow')]")
                    if follow_button.is_displayed():
                        follow_button.click()
                        logger.info("👥 Followed the post author.")
                        self._log_follow(follow_button.get_attribute("href"))
                        time.sleep(1)
                except NoSuchElementException:
                    logger.debug("No follow button found.")
            except Exception as e:
                logger.warning(f"⚠️ Issue engaging with post: {e}")
                continue

    # ===================================
    # FOLLOW TRACKING
    # ===================================
    def _log_follow(self, profile_url):
        if not profile_url:
            return
        if not os.path.exists(FOLLOW_DB):
            data = {}
        else:
            with open(FOLLOW_DB, "r") as f:
                data = json.load(f)
        data[profile_url] = {
            "followed_at": datetime.utcnow().isoformat(),
            "status": "followed"
        }
        with open(FOLLOW_DB, "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f"📁 Logged new follow: {profile_url}")

    def unfollow_non_returners(self, days_threshold=3):
        if not os.path.exists(FOLLOW_DB):
            logger.warning("⚠️ No follow log found.")
            return
        with open(FOLLOW_DB, "r") as f:
            follows = json.load(f)
        now = datetime.utcnow()
        unfollowed = []
        for user, data in follows.items():
            followed_at = datetime.fromisoformat(data["followed_at"])
            if (now - followed_at).days >= days_threshold and data.get("status") == "followed":
                try:
                    self.driver.get(user)
                    unfollow_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Following')]")
                    unfollow_button.click()
                    logger.info(f"➖ Unfollowed {user}")
                    follows[user]["status"] = "unfollowed"
                    unfollowed.append(user)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to unfollow {user}: {e}")
        with open(FOLLOW_DB, "w") as f:
            json.dump(follows, f, indent=4)
        logger.info(f"✅ Unfollowed {len(unfollowed)} users.")

    # ===================================
    # DAILY SESSION RUNNER
    # ===================================
    def run_daily_session(self, post_prompt=None, viral_prompt=None):
        logger.info(f"🚀 Running daily session on {PLATFORM}")
        if not self.login():
            logger.error("❌ Login failed. Aborting session.")
            return
        # Post content if prompt provided
        if post_prompt:
            post_content = self.ai_agent.ask(
                prompt=post_prompt,
                metadata={"platform": PLATFORM, "persona": "Victor"}
            )
            self.post(post_content)
        self.engage_community(viral_prompt=viral_prompt)
        self.unfollow_non_returners()
        logger.info(f"✅ Daily session completed on {PLATFORM}")

# ===================================
# Unified Stocktwits Strategy Class
# ===================================
class StocktwitsStrategy(StocktwitsCommunityArchitect):
    """
    Centralized strategy class for Stocktwits automation and community building.
    Extends StocktwitsCommunityArchitect with:
      - Dynamic feedback loops (engagement metrics analysis).
      - AI sentiment analysis & reinforcement loops.
      - Reward system for top engagers.
      - Cross-platform feedback integration.
    """
    FEEDBACK_DB = "social/data/stocktwits_feedback_tracker.json"
    REWARD_DB = "social/data/stocktwits_reward_tracker.json"

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
        (For demonstration, metrics are incremented with random values.)
        """
        logger.info("📊 Analyzing Stocktwits engagement metrics...")
        self.feedback_data["upvotes"] = self.feedback_data.get("upvotes", 0) + random.randint(5, 10)
        self.feedback_data["comments"] = self.feedback_data.get("comments", 0) + random.randint(2, 5)
        self.feedback_data["subscriptions"] = self.feedback_data.get("subscriptions", 0) + random.randint(1, 3)
        logger.info(f"👍 Upvotes: {self.feedback_data['upvotes']}, 💬 Comments: {self.feedback_data['comments']}, ➕ Subscriptions: {self.feedback_data['subscriptions']}")
        self._save_feedback_data()

    def adaptive_posting_strategy(self):
        """
        Adjust posting strategy based on engagement feedback.
        """
        logger.info("🔄 Adapting Stocktwits posting strategy based on feedback...")
        if self.feedback_data.get("upvotes", 0) > 100:
            logger.info("🔥 High engagement detected! Consider increasing post frequency.")
        if self.feedback_data.get("comments", 0) > 50:
            logger.info("💡 More discussion-oriented posts may boost community interaction.")

    def analyze_comment_sentiment(self, comment):
        """
        Analyze the sentiment of a comment using AI.
        Returns 'positive', 'neutral', or 'negative'.
        """
        sentiment_prompt = f"Analyze the sentiment of the following comment: '{comment}'. Respond with positive, neutral, or negative."
        sentiment = self.ai_agent.ask(prompt=sentiment_prompt, metadata={"platform": PLATFORM, "persona": "Victor"})
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
            response = self.ai_agent.ask(prompt=reinforcement_prompt, metadata={"platform": PLATFORM, "persona": "Victor"})
            logger.info(f"Reinforcement response generated: {response}")
            # Optionally, automate replying to the comment here.
            return response
        return None

    def reward_top_engagers(self):
        """
        Reward top community engagers with custom shout-outs.
        """
        logger.info("🎉 Evaluating top engagers for rewards on Stocktwits...")
        if os.path.exists(self.REWARD_DB):
            with open(self.REWARD_DB, "r") as f:
                reward_data = json.load(f)
        else:
            reward_data = {}
        # Stub: For demo purposes, randomly pick a profile from follow log
        if os.path.exists(FOLLOW_DB):
            with open(FOLLOW_DB, "r") as f:
                follow_data = json.load(f)
            top_profile = max(follow_data.items(), key=lambda x: random.random(), default=(None, None))[0]
            if top_profile and top_profile not in reward_data:
                custom_message = f"Hey, thanks for your stellar engagement! Your support drives our community forward."
                reward_data[top_profile] = {"rewarded_at": datetime.utcnow().isoformat(), "message": custom_message}
                logger.info(f"Reward issued to: {top_profile}")
                write_json_log(PLATFORM, "success", tags=["reward"], ai_output=top_profile)
        else:
            logger.warning("No follow data available for rewards on Stocktwits.")
        with open(self.REWARD_DB, "w") as f:
            json.dump(reward_data, f, indent=4)

    def cross_platform_feedback_loop(self):
        """
        Merge Stocktwits engagement data with that from other platforms (stub implementation).
        """
        logger.info("🌐 Merging cross-platform feedback loops for Stocktwits...")
        twitter_data = {"upvotes": random.randint(8, 15), "comments": random.randint(3, 8)}
        facebook_data = {"upvotes": random.randint(10, 20), "comments": random.randint(5, 10)}
        unified_metrics = {
            "stocktwits": self.feedback_data,
            "twitter": twitter_data,
            "facebook": facebook_data
        }
        logger.info(f"Unified Metrics: {unified_metrics}")

    def run_feedback_loop(self):
        self.analyze_engagement_metrics()
        self.adaptive_posting_strategy()

    def run_daily_strategy_session(self, post_prompt=None, viral_prompt=None):
        """
        Full daily strategy session:
          - Run the standard daily session.
          - Process feedback, analyze sentiment, and reinforce engagement.
          - Reward top engagers.
          - Merge cross-platform engagement data.
        """
        logger.info("🚀 Starting Full Stocktwits Strategy Session.")
        self.run_daily_session(post_prompt=post_prompt, viral_prompt=viral_prompt)
        # Process sample comments for reinforcement (stub example)
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
        logger.info("✅ Stocktwits Strategy Session Complete.")

# ===================================
# Autonomous Execution Example
# ===================================
if __name__ == "__main__":
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    stocktwits_bot = StocktwitsStrategy(driver)

    post_prompt = (
        "Write a Stocktwits post about how AI-driven systems revolutionize trading strategies. "
        "Make it raw, insightful, and community-driven."
    )

    viral_prompt = (
        "Write a comment that sparks discussion around AI trading and system convergence. "
        "Be authentic, insightful, and community-focused."
    )

    stocktwits_bot.run_daily_strategy_session(post_prompt=post_prompt, viral_prompt=viral_prompt)
    driver.quit()
