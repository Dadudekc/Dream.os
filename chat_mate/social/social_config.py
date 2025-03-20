import os
import json
import time
import logging
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger("SocialConfigWithRateLimits")

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

class SocialConfig:
    """
    FULL SYNC social_config with integrated rate limit and daily reset handling.
    """

    RATE_LIMIT_STATE_FILE = "rate_limit_state.json"

    def __init__(self):
        self.env = os.environ
        self.platform_urls = self._default_platform_urls()
        self.rate_limits = self._default_rate_limits()
        self.last_action_times = defaultdict(lambda: 0)
        self.action_counters = defaultdict(lambda: 0)
        self.last_reset_time = datetime.utcnow()

        self._validate_required_keys()
        self._load_rate_limit_state()

    # ------------------------------
    # ENV AND PLATFORM MANAGEMENT
    # ------------------------------
    def get_env(self, key: str, default=None) -> str:
        return self.env.get(key, default)

    def _validate_required_keys(self):
        required_keys = [
            "LINKEDIN_EMAIL", "LINKEDIN_PASSWORD",
            "TWITTER_EMAIL", "TWITTER_PASSWORD",
            "FACEBOOK_EMAIL", "FACEBOOK_PASSWORD",
            "INSTAGRAM_EMAIL", "INSTAGRAM_PASSWORD",
            "REDDIT_USERNAME", "REDDIT_PASSWORD",
            "STOCKTWITS_USERNAME", "STOCKTWITS_PASSWORD"
        ]

        missing = [key for key in required_keys if not self.get_env(key)]
        if missing:
            logger.warning(f"⚠️ Missing required env vars: {missing}")

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
        urls = self.platform_urls.get(platform, {})
        return urls.get(key, "")

    @property
    def chrome_profile_path(self):
        return self.get_env("CHROME_PROFILE_PATH", os.path.join(os.getcwd(), "chrome_profiles"))

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
            logger.warning(f"⚠️ No rate limits defined for {platform}:{action}")
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
            logger.warning(f"🚫 Daily limit reached for {platform}:{action}. Max: {daily_max}")
            return False

        logger.info(f"✅ Within rate limits for {platform}:{action}.")
        return True

    def register_action(self, platform: str, action: str):
        now = time.time()
        self.last_action_times[(platform, action)] = now
        self.action_counters[(platform, action)] += 1

        logger.info(f"📈 Registered {platform}:{action}. Count today: {self.action_counters[(platform, action)]}")
        self._save_rate_limit_state()

    def _check_daily_reset(self):
        """Resets daily counters after 24 hours."""
        now = datetime.utcnow()
        if now - self.last_reset_time >= timedelta(hours=24):
            logger.info("🔄 Resetting daily action counters...")
            self.action_counters.clear()
            self.last_reset_time = now
            self._save_rate_limit_state()

    # ------------------------------
    # PERSISTENCE: SAVE + LOAD STATE
    # ------------------------------
    def _save_rate_limit_state(self):
        """Persist rate limit counters and last reset time."""
        state = {
            "action_counters": dict(self.action_counters),
            "last_action_times": dict(self.last_action_times),
            "last_reset_time": self.last_reset_time.isoformat()
        }

        with open(self.RATE_LIMIT_STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)

        logger.info(f"💾 Rate limit state saved to {self.RATE_LIMIT_STATE_FILE}")

    def _load_rate_limit_state(self):
        """Restore rate limit counters and last reset time."""
        if not os.path.exists(self.RATE_LIMIT_STATE_FILE):
            logger.info(f"ℹ️ No saved rate limit state found at {self.RATE_LIMIT_STATE_FILE}. Starting fresh.")
            return

        try:
            with open(self.RATE_LIMIT_STATE_FILE, "r") as f:
                state = json.load(f)

            self.action_counters = defaultdict(lambda: 0, state.get("action_counters", {}))
            self.last_action_times = defaultdict(lambda: 0, state.get("last_action_times", {}))
            self.last_reset_time = datetime.fromisoformat(state.get("last_reset_time"))

            logger.info(f"✅ Rate limit state restored from {self.RATE_LIMIT_STATE_FILE}")

        except Exception as e:
            logger.error(f"❌ Failed to load rate limit state: {e}")

    # ------------------------------
    # DYNAMIC LIMIT MANAGEMENT
    # ------------------------------
    def register_rate_limit(self, platform: str, action: str, cooldown: int, daily_max: int):
        """Register or update rate limits for a platform-action pair."""
        if platform not in self.rate_limits:
            self.rate_limits[platform] = {}

        self.rate_limits[platform][action] = {
            "cooldown": cooldown,
            "daily_max": daily_max
        }

        logger.info(f"✅ Registered new rate limit: {platform}:{action} - Cooldown: {cooldown}s, Daily Max: {daily_max}")


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
