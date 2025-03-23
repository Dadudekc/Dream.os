import os
import json
import time
import logging
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime, timedelta, UTC
from core.PathManager import PathManager  # Assuming this is where it's defined

logger = logging.getLogger(__name__)

# ------------------------------
# Bootstrap Env + Paths
# ------------------------------
# This should happen globally at bootstrap, but safe here if isolated
dotenv_path = PathManager.get_env_path(".env")  # Ensures cross-platform consistency
load_dotenv(dotenv_path)

# ------------------------------
# SocialConfig Class
# ------------------------------
class SocialConfig:
    """
    FULL SYNC social_config with integrated rate limit and daily reset handling.
    """

    def __init__(self):
        self.env = os.environ
        self.path_manager = PathManager()  # Singleton assumed
        self.platform_urls = self._default_platform_urls()
        self.rate_limits = self._default_rate_limits()
        self.last_action_times = defaultdict(lambda: 0)
        self.action_counters = defaultdict(lambda: 0)
        self.last_reset_time = datetime.now(UTC)
        self.rate_limit_state_path = self.path_manager.get_rate_limit_state_path()  # Cleaner

        self._validate_required_keys()
        self._load_rate_limit_state()

    # ------------------------------
    # ENV AND PLATFORM MANAGEMENT
    # ------------------------------
    def get_env(self, key: str, default=None) -> str:
        return self.env.get(key, default)

    def _validate_required_keys(self):
        missing = ["STOCKTWITS_USERNAME", "STOCKTWITS_PASSWORD"]  # Placeholder
        if missing:
            logger.warning(f"Missing required env vars: {missing}")

    def _default_platform_urls(self):
        return {
            "linkedin": {"login": "https://www.linkedin.com/login", "post": "https://www.linkedin.com/feed/"},
            "twitter": {"login": "https://twitter.com/login", "post": "https://twitter.com/compose/tweet"},
            "facebook": {"login": "https://www.facebook.com/login/", "post": "https://www.facebook.com/"},
            "instagram": {"login": "https://www.instagram.com/accounts/login/", "post": "https://www.instagram.com/create/style/"},
            "reddit": {"login": "https://www.reddit.com/login/", "post": "https://www.reddit.com/submit"},
            "stocktwits": {"login": "https://stocktwits.com/signin", "post": "https://stocktwits.com/post"}
        }

    def get_platform_url(self, platform: str, key: str) -> str:
        return self.platform_urls.get(platform, {}).get(key, "")

    @property
    def chrome_profile_path(self):
        return self.get_env("CHROME_PROFILE_PATH", self.path_manager.get_chrome_profile_path())

    # ------------------------------
    # RATE LIMIT MANAGEMENT
    # ------------------------------
    def _default_rate_limits(self):
        return {
            "twitter": {"post": {"cooldown": 60, "daily_max": 300}, "follow": {"cooldown": 10, "daily_max": 1000}},
            "linkedin": {"post": {"cooldown": 600, "daily_max": 20}, "message": {"cooldown": 30, "daily_max": 100}},
            "facebook": {"post": {"cooldown": 300, "daily_max": 50}},
            "instagram": {"post": {"cooldown": 3600, "daily_max": 10}, "follow": {"cooldown": 10, "daily_max": 200}},
            "reddit": {"post": {"cooldown": 600, "daily_max": 25}},
            "stocktwits": {"post": {"cooldown": 60, "daily_max": 200}}
        }

    def within_rate_limit(self, platform: str, action: str) -> bool:
        self._check_daily_reset()

        limits = self.rate_limits.get(platform, {}).get(action)
        if not limits:
            logger.warning(f"No rate limits defined for {platform}:{action}")
            return True

        now = time.time()
        last_time = self.last_action_times[(platform, action)]
        cooldown = limits["cooldown"]
        daily_max = limits["daily_max"]
        actions_today = self.action_counters[(platform, action)]

        if now - last_time < cooldown:
            remaining = cooldown - (now - last_time)
            logger.info(f"⏳ Cooldown active for {platform}:{action} - {remaining:.2f}s remaining.")
            return False

        if actions_today >= daily_max:
            logger.warning(f" Daily limit reached for {platform}:{action}. Max: {daily_max}")
            return False

        logger.info(f" Within rate limits for {platform}:{action}.")
        return True

    def register_action(self, platform: str, action: str):
        now = time.time()
        self.last_action_times[(platform, action)] = now
        self.action_counters[(platform, action)] += 1

        logger.info(f" Registered {platform}:{action}. Count today: {self.action_counters[(platform, action)]}")
        self._save_rate_limit_state()

    def _check_daily_reset(self):
        now = datetime.now(UTC)
        if now - self.last_reset_time >= timedelta(hours=24):
            logger.info(" Resetting daily action counters...")
            self.action_counters.clear()
            self.last_reset_time = now
            self._save_rate_limit_state()

    # ------------------------------
    # PERSISTENCE: SAVE + LOAD STATE
    # ------------------------------
    def _save_rate_limit_state(self):
        state = {
            "action_counters": dict(self.action_counters),
            "last_action_times": dict(self.last_action_times),
            "last_reset_time": self.last_reset_time.isoformat()
        }

        try:
            with open(self.rate_limit_state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
            logger.info(f" Rate limit state saved to {self.rate_limit_state_path}")
        except Exception as e:
            logger.error(f" Failed to save rate limit state: {e}")

    def _load_rate_limit_state(self):
        logger.info(f"No saved rate limit state found at self.rate_limit_state_path. Starting fresh.")

    # ------------------------------
    # DYNAMIC LIMIT MANAGEMENT
    # ------------------------------
    def register_rate_limit(self, platform: str, action: str, cooldown: int, daily_max: int):
        if platform not in self.rate_limits:
            self.rate_limits[platform] = {}

        self.rate_limits[platform][action] = {
            "cooldown": cooldown,
            "daily_max": daily_max
        }

        logger.info(f" Registered new rate limit: {platform}:{action} - Cooldown: {cooldown}s, Daily Max: {daily_max}")


# ✅ Singleton instance
social_config = SocialConfig()

# ------------------------------
# Example Usage (Local Testing)
# ------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    platform = "linkedin"
    action = "post"

    if social_config.within_rate_limit(platform, action):
        print(f"Posting to {platform}...")
        social_config.register_action(platform, action)
    else:
        print(f"Rate limit exceeded. Retry later.")
