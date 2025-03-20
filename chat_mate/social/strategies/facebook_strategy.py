import os
import sys
import random
import shutil
import logging
import time
import json
from functools import wraps
from datetime import datetime
from dotenv import load_dotenv

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Ensure .env variables are loaded
load_dotenv()

# Absolute imports from our codebase
from utils.cookie_manager import CookieManager
from social.log_writer import logger, write_json_log
from social.social_config import social_config
from social.AIChatAgent import AIChatAgent

MAX_ATTEMPTS = 3
DEFAULT_WAIT = 10

def retry_on_failure(max_attempts=MAX_ATTEMPTS, delay=2):
    """
    Decorator to retry a function on failure with a delay between attempts.
    """
    def decorator_retry(func):
        @wraps(func)
        def wrapper_retry(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    logger.warning(f"Attempt {attempts} failed in {func.__name__} due to: {e}")
                    time.sleep(delay * attempts)
            logger.error(f"All {max_attempts} attempts failed in {func.__name__}.")
            raise Exception(f"Max retry reached for {func.__name__}")
        return wrapper_retry
    return decorator_retry

def get_random_user_agent():
    """
    Returns a random user agent string from a predefined list.
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    ]
    return random.choice(user_agents)

# -------------------------------------------------
# FacebookBot Base Class
# -------------------------------------------------
class FacebookBot:
    """
    Automates Facebook login and posting.
    This base class handles authentication and AI-powered post creation.
    """
    PLATFORM = "facebook"

    def __init__(self, driver=None, wait_range=(3, 6)):
        self.platform = self.PLATFORM
        self.driver = driver or self.get_driver()
        self.wait_min, self.wait_max = wait_range
        self.cookie_manager = CookieManager()
        self.login_url = social_config.get_platform_url(self.platform, "login")
        self.post_url = social_config.get_platform_url(self.platform, "post")
        self.settings_url = social_config.get_platform_url(self.platform, "settings")
        self.email = social_config.get_env("FACEBOOK_EMAIL")
        self.password = social_config.get_env("FACEBOOK_PASSWORD")
        self.ai_agent = AIChatAgent(model="gpt-4o", tone="Victor", provider="openai")

    def _wait(self, custom_range=None):
        wait_time = random.uniform(*(custom_range or (self.wait_min, self.wait_max)))
        logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)

    def get_driver(self):
        chrome_options = webdriver.ChromeOptions()
        profile_path = social_config.get_env("CHROME_PROFILE_PATH", os.path.join(os.getcwd(), "chrome_profile"))
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument(f"--user-data-dir={profile_path}")
        chrome_options.add_argument(f"user-agent={get_random_user_agent()}")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info(f"Chrome driver initialized with profile: {profile_path}")
        return driver

    @retry_on_failure()
    def is_logged_in(self):
        """
        Verify login by navigating to the Facebook settings page.
        """
        self.driver.get(self.settings_url)
        WebDriverWait(self.driver, DEFAULT_WAIT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self._wait((3, 5))
        if "login" not in self.driver.current_url.lower():
            logger.info(f"✅ {self.platform.capitalize()} login confirmed via settings.")
            return True
        logger.debug(f"🔎 {self.platform.capitalize()} login check failed.")
        return False

    @retry_on_failure()
    def login(self):
        """
        Automate the Facebook login flow.
        """
        logger.info(f"🌐 Initiating login process for {self.platform.capitalize()}.")
        self.driver.get(self.login_url)
        self._wait()
        self.cookie_manager.load_cookies(self.driver, self.platform)
        self.driver.refresh()
        self._wait()
        if self.is_logged_in():
            logger.info(f"✅ Logged into {self.platform.capitalize()} via cookies.")
            write_json_log(self.platform, "successful", tags=["cookie_login"])
            return True
        if not self.email or not self.password:
            logger.warning(f"⚠️ No {self.platform} credentials provided.")
            write_json_log(self.platform, "failed", tags=["auto_login"], ai_output="Missing credentials.")
            return False
        try:
            email_field = WebDriverWait(self.driver, DEFAULT_WAIT).until(EC.visibility_of_element_located((By.ID, "email")))
            pass_field = WebDriverWait(self.driver, DEFAULT_WAIT).until(EC.visibility_of_element_located((By.ID, "pass")))
            email_field.clear()
            pass_field.clear()
            email_field.send_keys(self.email)
            pass_field.send_keys(self.password)
            pass_field.send_keys(Keys.RETURN)
            logger.info(f"📨 Submitted credentials for {self.platform.capitalize()}.")
            WebDriverWait(self.driver, DEFAULT_WAIT).until(EC.url_changes(self.login_url))
            self._wait((5, 10))
        except Exception as e:
            logger.error(f"🚨 Error during {self.platform.capitalize()} auto-login: {e}")
            write_json_log(self.platform, "failed", tags=["auto_login"], ai_output=str(e))
        if not self.is_logged_in():
            logger.warning(f"⚠️ Auto-login failed for {self.platform.capitalize()}. Awaiting manual login...")
            if self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, self.platform):
                write_json_log(self.platform, "successful", tags=["manual_login"])
            else:
                msg = "Manual login failed."
                logger.error(f"❌ {msg} for {self.platform.capitalize()}.")
                write_json_log(self.platform, "failed", tags=["manual_login"], ai_output=msg)
                return False
        self.cookie_manager.save_cookies(self.driver, self.platform)
        logger.info(f"✅ Logged in successfully to {self.platform.capitalize()}.")
        write_json_log(self.platform, "successful", tags=["auto_login"])
        return True

    @retry_on_failure()
    def post(self, content_prompt):
        """
        Publish a Facebook post with AI-generated content.
        """
        logger.info(f"🚀 Attempting to post on {self.platform.capitalize()}.")
        if not self.is_logged_in():
            msg = "Not logged in."
            logger.warning(f"⚠️ Cannot post to {self.platform.capitalize()}: {msg}")
            write_json_log(self.platform, "failed", tags=["post"], ai_output=msg)
            return {"platform": self.platform, "status": "failed", "details": msg}
        content = self.ai_agent.ask(
            prompt=content_prompt,
            additional_context="This post reflects my authentic, raw, and strategic voice.",
            metadata={"platform": "Facebook", "persona": "Victor"}
        ) or content_prompt
        try:
            self.driver.get(self.post_url)
            self._wait((5, 8))
            create_post_button = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Create a post']"))
            )
            create_post_button.click()
            self._wait((2, 3))
            post_box = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.visibility_of_element_located((By.XPATH, "//div[@role='textbox']"))
            )
            post_box.send_keys(content)
            self._wait((2, 3))
            post_button = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Post']"))
            )
            post_button.click()
            self._wait((5, 8))
            logger.info(f"✅ Post published on {self.platform.capitalize()} in my authentic voice.")
            write_json_log(self.platform, "successful", tags=["post"])
            return {"platform": self.platform, "status": "success", "details": "Post published"}
        except Exception as e:
            logger.error(f"🚨 Failed to post on {self.platform.capitalize()}: {e}")
            write_json_log(self.platform, "failed", tags=["post"], ai_output=str(e))
            return {"platform": self.platform, "status": "failed", "details": str(e)}

# -------------------------------------------------
# FacebookEngagementBot Class
# -------------------------------------------------
class FacebookEngagementBot(FacebookBot):
    """
    Extends FacebookBot with essential community building functions:
      - Like posts, comment, follow/unfollow users, and viral engagement.
      - Maintains a FOLLOW_DB to track engagements.
      - Runs daily engagement sessions.
    """
    FOLLOW_DB = "social/data/friend_tracker.json"

    def like_posts(self):
        """
        Like posts on Facebook pages or groups.
        """
        trending_url = social_config.get_platform_url(self.platform, "trending")
        self.driver.get(trending_url)
        self._wait((5, 8))
        posts = self.driver.find_elements(By.CSS_SELECTOR, "div[data-pagelet='FeedUnit']")
        liked = 0
        for post in posts:
            if liked >= random.randint(3, 6):
                break
            try:
                like_button = post.find_element(By.XPATH, ".//div[contains(@aria-label, 'Like')]")
                like_button.click()
                logger.info("❤️ Liked a post on Facebook.")
                liked += 1
                self._wait((2, 4))
            except Exception as e:
                logger.warning(f"⚠️ Could not like a post: {e}")

    def comment_on_posts(self, comments):
        """
        Comment on posts with AI-generated content.
        """
        trending_url = social_config.get_platform_url(self.platform, "trending")
        self.driver.get(trending_url)
        self._wait((5, 8))
        posts = self.driver.find_elements(By.CSS_SELECTOR, "div[data-pagelet='FeedUnit']")
        commented = 0
        for post in posts:
            if commented >= random.randint(2, 4):
                break
            try:
                comment_box = post.find_element(By.XPATH, ".//div[contains(@aria-label, 'Write a comment')]")
                comment = random.choice(comments)
                comment_box.click()
                comment_box.send_keys(comment)
                comment_box.send_keys(Keys.RETURN)
                logger.info(f"💬 Commented: '{comment}' on a post.")
                commented += 1
                self._wait((4, 6))
            except Exception as e:
                logger.warning(f"⚠️ Could not comment on a post: {e}")

    def follow_users(self):
        """
        Follow users by sending friend requests based on post interactions.
        """
        trending_url = social_config.get_platform_url(self.platform, "trending")
        self.driver.get(trending_url)
        self._wait((5, 8))
        posts = self.driver.find_elements(By.CSS_SELECTOR, "div[data-pagelet='FeedUnit']")
        followed = 0
        followed_users = []
        for post in posts:
            if followed >= random.randint(2, 5):
                break
            try:
                profile_link = post.find_element(By.XPATH, ".//a[contains(@href, 'profile.php') or contains(@href, '/')]")
                profile_url = profile_link.get_attribute("href")
                self.driver.get(profile_url)
                self._wait((3, 6))
                follow_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Add Friend') or contains(text(), 'Follow')]")
                follow_button.click()
                logger.info(f"➕ Sent friend request to: {profile_url}")
                write_json_log(self.platform, "successful", tags=["follow"], ai_output=profile_url)
                followed += 1
                followed_users.append(profile_url)
                self._wait((10, 15))
            except Exception as e:
                logger.error(f"❌ Error following user from post: {e}")
        return followed_users

    def unfollow_non_returners(self, days_threshold=3):
        """
        Unfollow users who haven't reciprocated the connection after a threshold.
        """
        if not os.path.exists(self.FOLLOW_DB):
            logger.warning("⚠️ No friend tracker data found.")
            return
        with open(self.FOLLOW_DB, "r") as f:
            follow_data = json.load(f)
        now = datetime.utcnow()
        unfollowed = []
        for user, data in follow_data.items():
            followed_at = datetime.fromisoformat(data["followed_at"])
            if (now - followed_at).days >= days_threshold and data.get("status") == "followed":
                try:
                    self.driver.get(user)
                    self._wait((3, 6))
                    unfollow_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Friends') or contains(text(), 'Following')]")
                    unfollow_button.click()
                    self._wait((1, 3))
                    confirm_button = self.driver.find_element(By.XPATH, "//button[text()='Unfriend']")
                    confirm_button.click()
                    logger.info(f"➖ Unfriended: {user}")
                    follow_data[user]["status"] = "unfriended"
                    unfollowed.append(user)
                except Exception as e:
                    logger.error(f"❌ Error unfriending {user}: {e}")
        with open(self.FOLLOW_DB, "w") as f:
            json.dump(follow_data, f, indent=4)
        logger.info(f"➖ Unfriended {len(unfollowed)} users.")

    def _log_followed_users(self, users):
        """
        Log new friend requests in a tracker for future follow-up.
        """
        if not users:
            return
        if os.path.exists(self.FOLLOW_DB):
            with open(self.FOLLOW_DB, "r") as f:
                follow_data = json.load(f)
        else:
            follow_data = {}
        for user in users:
            follow_data[user] = {"followed_at": datetime.utcnow().isoformat(), "status": "followed"}
        with open(self.FOLLOW_DB, "w") as f:
            json.dump(follow_data, f, indent=4)
        logger.info(f"💾 Logged {len(users)} new friend requests.")

    def go_viral(self):
        """
        Engage with trending posts by liking and commenting with AI-generated viral content.
        """
        viral_prompt = (
            "Compose a brief, authentic comment that is energetic, engaging, and invites discussion "
            "about market trends and system convergence."
        )
        trending_url = social_config.get_platform_url(self.platform, "trending")
        self.driver.get(trending_url)
        self._wait((3, 5))
        posts = self.driver.find_elements(By.CSS_SELECTOR, "div[data-pagelet='FeedUnit']")
        if not posts:
            logger.warning("⚠️ No trending posts found for viral engagement.")
            return
        random.shuffle(posts)
        for post in posts[:3]:
            try:
                like_button = post.find_element(By.XPATH, ".//div[contains(@aria-label, 'Like')]")
                like_button.click()
                logger.info("⬆️ Viral mode: Liked a trending post.")
                self._wait((1, 2))
                post_content = post.text
                comment = self.ai_agent.ask(
                    prompt=viral_prompt,
                    additional_context=f"Post content: {post_content}",
                    metadata={"platform": "Facebook", "persona": "Victor", "engagement": "viral"}
                )
                comment_box = post.find_element(By.XPATH, ".//div[contains(@aria-label, 'Write a comment')]")
                comment_box.click()
                comment_box.send_keys(comment)
                comment_box.send_keys(Keys.RETURN)
                logger.info(f"💬 Viral mode: Commented: {comment}")
                self._wait((2, 3))
            except Exception as e:
                logger.warning(f"⚠️ Viral engagement error on a trending post: {e}")
                continue

    def run_daily_session(self):
        """
        Run a full daily engagement session:
          - Log in (if needed)
          - Like posts, comment, follow users, unfollow non-returners, and go viral.
        """
        logger.info("🚀 Starting Facebook Daily Engagement Session")
        if not self.login():
            logger.error("❌ Facebook login failed. Ending session.")
            return
        # Generate AI-powered comments for engagement
        comments = []
        for tag in ["systemconvergence", "strategicgrowth", "automation"]:
            prompt = (
                f"You are Victor. Write a raw, authentic comment on a post about #{tag}. "
                "Inspire deep community discussion."
            )
            response = self.ai_agent.ask(prompt)
            comments.append(response.strip())
        self.like_posts()
        self.comment_on_posts(comments)
        followed = self.follow_users()
        if followed:
            self._log_followed_users(followed)
        self.unfollow_non_returners()
        self.go_viral()
        logger.info("✅ Facebook Daily Engagement Session Complete.")

# -------------------------------------------------
# FacebookStrategy Class (Unified Approach)
# -------------------------------------------------
class FacebookStrategy(FacebookEngagementBot):
    """
    Centralized strategy class for managing Facebook automation and community building.
    Inherits FacebookEngagementBot for core engagement functionality.
    Adds:
      - Dynamic feedback loops with AI sentiment analysis.
      - Reinforcement loops using ChatGPT responses in my voice.
      - A reward system for top engaging followers.
      - Cross-platform feedback loops to merge data from Instagram and Twitter.
    """
    FEEDBACK_DB = "social/data/feedback_tracker.json"
    REWARD_DB = "social/data/reward_tracker.json"

    def __init__(self, driver=None):
        super().__init__(driver=driver)
        self.feedback_data = self._load_feedback_data()

    def _load_feedback_data(self):
        """
        Load or initialize feedback data for engagement optimization.
        """
        if os.path.exists(self.FEEDBACK_DB):
            with open(self.FEEDBACK_DB, "r") as f:
                return json.load(f)
        return {}

    def _save_feedback_data(self):
        """
        Save updated feedback data for future use.
        """
        with open(self.FEEDBACK_DB, "w") as f:
            json.dump(self.feedback_data, f, indent=4)

    def analyze_engagement_metrics(self):
        """
        Analyze engagement results to optimize strategy.
        Updates self.feedback_data with metrics such as:
        - Most engaged posts
        - Best performing comments
        - Follower growth patterns
        """
        logger.info("📊 Analyzing Facebook engagement metrics...")
        # For demo purposes, increment metrics by random values
        self.feedback_data["likes"] = self.feedback_data.get("likes", 0) + random.randint(5, 10)
        self.feedback_data["comments"] = self.feedback_data.get("comments", 0) + random.randint(2, 5)
        self.feedback_data["follows"] = self.feedback_data.get("follows", 0) + random.randint(1, 3)

        logger.info(f"👍 Total Likes: {self.feedback_data['likes']}")
        logger.info(f"💬 Total Comments: {self.feedback_data['comments']}")
        logger.info(f"➕ Total Follows: {self.feedback_data['follows']}")
        self._save_feedback_data()

    def adaptive_posting_strategy(self):
        """
        Adjust posting strategy based on feedback loops.
        """
        logger.info("🔄 Adapting Facebook posting strategy based on feedback...")
        if self.feedback_data.get("likes", 0) > 100:
            logger.info("🔥 High engagement detected! Increasing post frequency.")
            # Hook into scheduler or additional sessions as needed.
        if self.feedback_data.get("comments", 0) > 50:
            logger.info("💡 Shifting to more community-focused discussion posts.")

    def analyze_comment_sentiment(self, comment):
        """
        Analyze the sentiment of a comment using AI.
        Returns 'positive', 'neutral', or 'negative'.
        """
        sentiment_prompt = f"Analyze the sentiment of the following comment: '{comment}'. Respond with positive, neutral, or negative."
        sentiment = self.ai_agent.ask(prompt=sentiment_prompt, metadata={"platform": "Facebook", "persona": "Victor"})
        sentiment = sentiment.strip().lower() if sentiment else "neutral"
        logger.info(f"Sentiment for comment '{comment}': {sentiment}")
        return sentiment

    def reinforce_engagement(self, comment):
        """
        If a comment is positive, generate a ChatGPT response in my voice to reinforce engagement.
        """
        sentiment = self.analyze_comment_sentiment(comment)
        if sentiment == "positive":
            reinforcement_prompt = f"As Victor, write an authentic, engaging response to: '{comment}' to reinforce community growth."
            response = self.ai_agent.ask(prompt=reinforcement_prompt, metadata={"platform": "Facebook", "persona": "Victor"})
            logger.info(f"Reinforcement response generated: {response}")
            # Here, you might automate sending the response as a comment or a direct message.
            return response
        return None

    def reward_top_followers(self):
        """
        Reward top engaging followers with custom messages and shout-outs.
        """
        logger.info("🎉 Evaluating top engaging followers for rewards...")
        # Load current reward data or initialize empty rewards.
        if os.path.exists(self.REWARD_DB):
            with open(self.REWARD_DB, "r") as f:
                reward_data = json.load(f)
        else:
            reward_data = {}

        # Stub: For demo, randomly pick a follower from friend tracker (if available).
        if os.path.exists(self.FOLLOW_DB):
            with open(self.FOLLOW_DB, "r") as f:
                follow_data = json.load(f)
            # Example: select top 1 engaged user based on a random metric
            top_follower = max(follow_data.items(), key=lambda x: random.random(), default=(None, None))[0]
            if top_follower and top_follower not in reward_data:
                custom_message = f"Hey there! Thanks for being an incredible supporter. Your engagement fuels our community's growth!"
                reward_data[top_follower] = {"rewarded_at": datetime.utcnow().isoformat(), "message": custom_message}
                logger.info(f"Reward issued to top follower: {top_follower}")
                write_json_log(self.platform, "successful", tags=["reward"], ai_output=top_follower)
        else:
            logger.warning("No follower data available to issue rewards.")

        with open(self.REWARD_DB, "w") as f:
            json.dump(reward_data, f, indent=4)

    def cross_platform_feedback_loop(self):
        """
        Merge engagement data from Instagram and Twitter with Facebook to create a unified strategy.
        """
        logger.info("🌐 Merging cross-platform feedback loops...")
        # Stub: In a real implementation, gather data from Instagram/Twitter APIs or logs.
        instagram_data = {"likes": random.randint(10, 20), "comments": random.randint(5, 10)}
        twitter_data = {"likes": random.randint(8, 15), "comments": random.randint(3, 8)}
        unified_metrics = {
            "facebook": self.feedback_data,
            "instagram": instagram_data,
            "twitter": twitter_data
        }
        logger.info(f"Unified Metrics: {unified_metrics}")
        # Here, you can add logic to adjust your posting and engagement strategy based on unified data.

    def run_feedback_loop(self):
        """
        Run the dynamic feedback loop process.
        """
        self.analyze_engagement_metrics()
        self.adaptive_posting_strategy()

    def run_daily_strategy_session(self):
        """
        Full daily strategy session:
          - Run the daily engagement session.
          - Process dynamic feedback loops.
          - Analyze and reinforce engagement through sentiment analysis.
          - Reward top followers.
          - Merge cross-platform feedback.
        """
        logger.info("🚀 Starting Full Facebook Strategy Session.")
        self.run_daily_session()
        # Example: Analyze sentiment for each comment made during the session
        sample_comments = [
            "This is amazing!",
            "Not really impressed.",
            "I love the authentic vibe."
        ]
        for comment in sample_comments:
            self.reinforce_engagement(comment)
        self.run_feedback_loop()
        self.reward_top_followers()
        self.cross_platform_feedback_loop()
        logger.info("✅ Facebook Strategy Session Complete.")

# ------------------------------------------------------
# Scheduler Setup for Facebook Strategy Engagement
# ------------------------------------------------------
def start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    bot = FacebookStrategy(driver=driver)
    scheduler = BackgroundScheduler()

    # Schedule 3 strategy sessions per day at random hours
    for _ in range(3):
        hour = random.randint(8, 22)
        minute = random.randint(0, 59)
        scheduler.add_job(bot.run_daily_strategy_session, 'cron', hour=hour, minute=minute)

    scheduler.start()
    logger.info("🕒 Scheduler started for Facebook strategy engagement.")

# ------------------------------------------------------
# Functional Wrapper for Quick Facebook Posting
# ------------------------------------------------------
def post_to_facebook(driver, content, env):
    """
    Quick functional wrapper for posting to Facebook.
    """
    fb_bot = FacebookBot(driver=driver)
    return fb_bot.post(content)

# ------------------------------------------------------
# Main Entry Point for Autonomous Execution
# ------------------------------------------------------
if __name__ == "__main__":
    start_scheduler()
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Scheduler stopped by user.")
