import time
import json
import os
import random
from datetime import datetime
from typing import Dict, Any, List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, ElementClickInterceptedException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.cookie_manager import CookieManager
from social.social_config import social_config
from social.log_writer import write_json_log, get_social_logger
from social.AIChatAgent import AIChatAgent
from social.strategies.base_platform_strategy import BasePlatformStrategy
from utils.SentimentAnalyzer import SentimentAnalyzer

logger = get_social_logger()

PLATFORM = "twitter"
FOLLOW_DB = "social/data/twitter_follow_tracker.json"

class TwitterCommunityArchitect:
    """
    Ultimate Twitter Engagement Bot.
    Combines posting, commenting, following, and adaptive AI-powered interactions.
    """
    def __init__(self, env, driver):
        self.env = env
        self.driver = driver
        self.cookie_manager = CookieManager()
        self.ai_agent = AIChatAgent(model="gpt-4o", tone="Victor", provider="openai")

    # ========================
    # LOGIN SYSTEM
    # ========================
    def login(self):
        logger.info(f" Starting login for {PLATFORM}")
        login_url = social_config.get_platform_url(PLATFORM, "login")
        self.driver.get(login_url)
        time.sleep(3)
        self.cookie_manager.load_cookies(self.driver, PLATFORM)
        self.driver.refresh()
        time.sleep(3)
        if self.is_logged_in():
            logger.info(" Logged in via cookies")
            return True
        try:
            email = social_config.get_env("TWITTER_EMAIL")
            password = social_config.get_env("TWITTER_PASSWORD")
            email_field = self.driver.find_element(By.NAME, "text")
            email_field.send_keys(email, Keys.RETURN)
            time.sleep(3)
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.send_keys(password, Keys.RETURN)
            time.sleep(3)
        except Exception as e:
            logger.error(f" Auto-login failed: {e}")
        if self.is_logged_in():
            self.cookie_manager.save_cookies(self.driver, PLATFORM)
            return True
        logger.warning("️ Manual login fallback...")
        if self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, PLATFORM):
            self.cookie_manager.save_cookies(self.driver, PLATFORM)
            return True
        logger.error(" Manual login failed.")
        return False

    def is_logged_in(self):
        return "home" in self.driver.current_url

    # ========================
    # POSTING SYSTEM
    # ========================
    def post_tweet(self, content, retries=3):
        logger.info(f" Posting a tweet on {PLATFORM}")
        post_url = social_config.get_platform_url(PLATFORM, "post")
        for attempt in range(1, retries + 1):
            try:
                self.driver.get(post_url)
                time.sleep(3)
                textarea = self.driver.find_element(By.CSS_SELECTOR, "div[aria-label='Tweet text']")
                textarea.send_keys(content)
                time.sleep(1)
                post_button = self.driver.find_element(By.XPATH, "//div[@data-testid='tweetButtonInline']")
                post_button.click()
                time.sleep(3)
                logger.info(f" Tweet posted: {content[:50]}...")
                tweet_id = self._extract_tweet_id()
                return {"status": "success", "tweet_id": tweet_id}
            except Exception as e:
                logger.warning(f"️ Attempt {attempt} failed: {e}")
                time.sleep(2)
        logger.error(f" Failed to post after {retries} attempts.")
        return {"status": "failed"}

    def post_thread(self, content):
        logger.info(f" Dispatching Twitter thread...")
        tweets = content.strip().split("\n\n")
        for index, tweet in enumerate(tweets):
            result = self.post_tweet(tweet)
            if result["status"] != "success":
                return False
            time.sleep(3)
        logger.info(" Thread posted successfully.")
        return True

    def _extract_tweet_id(self):
        try:
            self.driver.get(social_config.get_platform_url(PLATFORM, "profile"))
            time.sleep(3)
            latest_tweet = self.driver.find_element(By.XPATH, "(//article[@data-testid='tweet'])[1]")
            return latest_tweet.get_attribute("data-tweet-id")
        except Exception as e:
            logger.warning(f"️ Failed to extract tweet ID: {e}")
            return None

    # ========================
    # COMMUNITY ENGAGEMENT
    # ========================
    def engage_community(self, search_query="trading", interactions=5):
        logger.info(f" Engaging community on {PLATFORM}")
        search_url = f"https://twitter.com/search?q={search_query}&src=typed_query&f=live"
        self.driver.get(search_url)
        time.sleep(5)
        posts = self.driver.find_elements(By.XPATH, "//article[@data-testid='tweet']")
        if not posts:
            logger.warning(f"️ No tweets found for {search_query}")
            return
        random.shuffle(posts)
        posts_to_engage = posts[:interactions]
        for post in posts_to_engage:
            try:
                # Like tweet
                like_button = post.find_element(By.XPATH, ".//div[@data-testid='like']")
                like_button.click()
                logger.info("️ Liked a tweet.")
                time.sleep(1)
                # Comment using AI
                comment_button = post.find_element(By.XPATH, ".//div[@data-testid='reply']")
                comment_button.click()
                time.sleep(2)
                comment_box = self.driver.find_element(By.XPATH, "//div[@aria-label='Tweet text']")
                comment_text = self.ai_agent.ask(
                    prompt="Write a brief, insightful comment on trading strategies.",
                    additional_context=post.text,
                    metadata={"platform": PLATFORM, "persona": "Victor", "engagement": "comment"}
                )
                comment_box.send_keys(comment_text)
                time.sleep(1)
                reply_button = self.driver.find_element(By.XPATH, "//div[@data-testid='tweetButton']")
                reply_button.click()
                logger.info(f" Comment posted: {comment_text}")
                time.sleep(3)
                # Optional: Follow the tweet's author
                self._follow_author(post)
            except Exception as e:
                logger.warning(f"️ Engagement failed: {e}")

    def _follow_author(self, post):
        try:
            follow_button = post.find_element(By.XPATH, ".//div[@role='button' and text()='Follow']")
            if follow_button.is_displayed():
                follow_button.click()
                profile_url = follow_button.get_attribute("href")
                logger.info(f" Followed author: {profile_url}")
                self._log_follow(profile_url)
        except NoSuchElementException:
            logger.debug("No follow button found.")

    # ========================
    # FOLLOW MANAGEMENT
    # ========================
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

    def unfollow_non_returners(self, days_threshold=3):
        if not os.path.exists(FOLLOW_DB):
            logger.warning("️ No follow tracker file.")
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
                    unfollow_button = self.driver.find_element(By.XPATH, "//div[@role='button' and text()='Following']")
                    unfollow_button.click()
                    logger.info(f" Unfollowed {user}")
                    follows[user]["status"] = "unfollowed"
                    unfollowed.append(user)
                except Exception as e:
                    logger.warning(f"️ Failed to unfollow {user}: {e}")
        with open(FOLLOW_DB, "w") as f:
            json.dump(follows, f, indent=4)
        logger.info(f" Unfollowed {len(unfollowed)} non-returners.")

    # ========================
    # DAILY SESSION RUNNER
    # ========================
    def run_daily_session(self, post_prompt, search_query="trading", interactions=5):
        logger.info(f" Starting daily session on {PLATFORM}")
        if not self.login():
            logger.error(" Login failed.")
            return
        # Post a thread using AI-generated content
        thread_content = self.ai_agent.ask(
            prompt=post_prompt,
            metadata={"platform": PLATFORM, "persona": "Victor", "engagement": "thread"}
        )
        self.post_thread(thread_content)
        # Engage community
        self.engage_community(search_query=search_query, interactions=interactions)
        # Unfollow non-returners
        self.unfollow_non_returners()
        logger.info(f" Daily session complete on {PLATFORM}")

    def post_thread(self, content):
        logger.info(" Dispatching Twitter thread...")
        tweets = content.strip().split("\n\n")
        for index, tweet in enumerate(tweets):
            result = self.post_tweet(tweet)
            if result["status"] != "success":
                return False
            time.sleep(3)
        logger.info(" Thread posted successfully.")
        return True

# ========================
# Unified Twitter Strategy Class
# ========================
class TwitterStrategy(TwitterCommunityArchitect):
    """
    Centralized strategy class for Twitter automation and community building.
    Extends TwitterCommunityArchitect with:
      - Dynamic feedback loops for engagement metrics analysis.
      - AI sentiment analysis & reinforcement loops.
      - Reward system for top engagers.
      - Cross-platform feedback integration.
    """
    FEEDBACK_DB = "social/data/twitter_feedback_tracker.json"
    REWARD_DB = "social/data/twitter_reward_tracker.json"

    def __init__(self, env, driver):
        super().__init__(env, driver)
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
        Analyze engagement and update metrics.
        For demo, metrics are incremented by random values.
        """
        logger.info(" Analyzing Twitter engagement metrics...")
        self.feedback_data["likes"] = self.feedback_data.get("likes", 0) + random.randint(5, 10)
        self.feedback_data["comments"] = self.feedback_data.get("comments", 0) + random.randint(2, 5)
        self.feedback_data["follows"] = self.feedback_data.get("follows", 0) + random.randint(1, 3)
        logger.info(f" Likes: {self.feedback_data['likes']},  Comments: {self.feedback_data['comments']},  Follows: {self.feedback_data['follows']}")
        self._save_feedback_data()

    def adaptive_posting_strategy(self):
        """
        Adjust posting strategy based on feedback.
        """
        logger.info(" Adapting Twitter posting strategy based on feedback...")
        if self.feedback_data.get("likes", 0) > 100:
            logger.info(" High engagement detected! Consider increasing tweet frequency.")
        if self.feedback_data.get("comments", 0) > 50:
            logger.info(" More discussion-driven tweets may boost engagement.")

    def analyze_comment_sentiment(self, comment):
        """
        Analyze sentiment of a comment using AI.
        Returns 'positive', 'neutral', or 'negative'.
        """
        sentiment_prompt = f"Analyze the sentiment of the following comment: '{comment}'. Respond with positive, neutral, or negative."
        sentiment = self.ai_agent.ask(prompt=sentiment_prompt, metadata={"platform": PLATFORM, "persona": "Victor"})
        sentiment = sentiment.strip().lower() if sentiment else "neutral"
        logger.info(f"Sentiment for comment '{comment}': {sentiment}")
        return sentiment

    def reinforce_engagement(self, comment):
        """
        If a comment is positive, generate a reinforcing response.
        """
        sentiment = self.analyze_comment_sentiment(comment)
        if sentiment == "positive":
            reinforcement_prompt = f"As Victor, write an engaging response to: '{comment}' to further boost community spirit."
            response = self.ai_agent.ask(prompt=reinforcement_prompt, metadata={"platform": PLATFORM, "persona": "Victor"})
            logger.info(f"Reinforcement response generated: {response}")
            # Optionally, automate replying here.
            return response
        return None

    def reward_top_engagers(self):
        """
        Reward top engagers with custom shout-outs.
        """
        logger.info(" Evaluating top engagers for rewards on Twitter...")
        if os.path.exists(self.REWARD_DB):
            with open(self.REWARD_DB, "r") as f:
                reward_data = json.load(f)
        else:
            reward_data = {}
        # Stub: randomly pick a profile from follow tracker
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
            logger.warning("No follow data available for rewards on Twitter.")
        with open(self.REWARD_DB, "w") as f:
            json.dump(reward_data, f, indent=4)

    def cross_platform_feedback_loop(self):
        """
        Merge Twitter engagement data with that from other platforms (stub).
        """
        logger.info(" Merging cross-platform feedback loops for Twitter...")
        facebook_data = {"likes": random.randint(10, 20), "comments": random.randint(5, 10)}
        reddit_data = {"likes": random.randint(8, 15), "comments": random.randint(3, 8)}
        unified_metrics = {
            "twitter": self.feedback_data,
            "facebook": facebook_data,
            "reddit": reddit_data
        }
        logger.info(f"Unified Metrics: {unified_metrics}")

    def run_feedback_loop(self):
        self.analyze_engagement_metrics()
        self.adaptive_posting_strategy()

    def run_daily_strategy_session(self, post_prompt, search_query="trading", interactions=5):
        """
        Full daily strategy session:
          - Run standard daily session.
          - Process feedback, analyze sentiment, and reinforce engagement.
          - Reward top engagers.
          - Merge cross-platform data.
        """
        logger.info(" Starting Full Twitter Strategy Session.")
        self.run_daily_session(post_prompt=post_prompt, search_query=search_query, interactions=interactions)
        # Process sample comments for reinforcement (stub)
        sample_comments = [
            "This is incredible!",
            "Not impressed by this tweet.",
            "I love the authentic vibe here."
        ]
        for comment in sample_comments:
            self.reinforce_engagement(comment)
        self.run_feedback_loop()
        self.reward_top_engagers()
        self.cross_platform_feedback_loop()
        logger.info(" Twitter Strategy Session Complete.")

# ========================
# Autonomous Execution Example
# ========================
if __name__ == "__main__":
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("chat_mate/social/templates"))
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    bot = TwitterStrategy(env=env, driver=driver)

    post_prompt = (
        "Write a Twitter thread about how AI-driven systems create unstoppable momentum in trading and automation."
    )

    bot.run_daily_strategy_session(post_prompt=post_prompt, search_query="trading", interactions=5)
    driver.quit()
