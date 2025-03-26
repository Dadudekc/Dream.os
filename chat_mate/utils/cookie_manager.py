import os
import pickle
from .logging_utils import logger, write_json_log

class CookieManager:
    """
    Manages loading, saving, and validating cookies for different platforms.
    """

    def __init__(self, cookie_dir="cookies", max_attempts=3):
        """
        Initialize the CookieManager.

        Args:
            cookie_dir (str): Directory to save/load cookies.
            max_attempts (int): Max manual login attempts before failing.
        """
        self.cookie_dir = cookie_dir
        os.makedirs(self.cookie_dir, exist_ok=True)

        self.logger = logger
        self.max_attempts = max_attempts

    def _get_cookie_path(self, platform):
        return os.path.join(self.cookie_dir, f"{platform}.pkl")

    def load_cookies(self, driver, platform):
        """
        Load cookies into the provided WebDriver session.

        Args:
            driver (selenium.webdriver): The Selenium WebDriver instance.
            platform (str): Name of the platform (e.g., 'facebook').

        Returns:
            bool: True if cookies loaded successfully, False otherwise.
        """
        cookie_path = self._get_cookie_path(platform)

        if not os.path.exists(cookie_path):
            msg = f"⚠️ No cookie file found for {platform} at {cookie_path}"
            self.logger.warning(msg)
            write_json_log(platform, "failed", tags=["cookie_load"], ai_output=msg)
            return False

        try:
            with open(cookie_path, "rb") as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    cookie.pop("sameSite", None)
                    try:
                        driver.add_cookie(cookie)
                    except Exception as e:
                        self.logger.error(" Error adding cookie for %s: %s", platform, e)
                        write_json_log(platform, "failed", tags=["cookie_add"], ai_output=str(e))

            msg = f"✅ Loaded cookies for {platform}"
            self.logger.info(msg)
            write_json_log(platform, "successful", tags=["cookie_load"])
            return True

        except Exception as e:
            msg = f"❌ Failed to load cookies for {platform}: {e}"
            self.logger.error(msg)
            write_json_log(platform, "failed", tags=["cookie_load"], ai_output=str(e))
            return False

    def save_cookies(self, driver, platform):
        """
        Save cookies from the provided WebDriver session.

        Args:
            driver (selenium.webdriver): The Selenium WebDriver instance.
            platform (str): Name of the platform (e.g., 'facebook').

        Returns:
            bool: True if cookies saved successfully, False otherwise.
        """
        cookie_path = self._get_cookie_path(platform)

        try:
            with open(cookie_path, "wb") as file:
                pickle.dump(driver.get_cookies(), file)

            msg = f"💾 Saved cookies for {platform}"
            self.logger.info(msg)
            write_json_log(platform, "successful", tags=["cookie_save"])
            return True

        except Exception as e:
            msg = f"❌ Failed to save cookies for {platform}: {e}"
            self.logger.error(msg)
            write_json_log(platform, "failed", tags=["cookie_save"], ai_output=str(e))
            return False

    def wait_for_manual_login(self, driver, check_func, platform):
        """
        Wait for manual login completion and save cookies when successful.

        Args:
            driver (selenium.webdriver): The Selenium WebDriver instance.
            check_func (function): Function that checks whether the user is logged in.
            platform (str): Name of the platform (e.g., 'facebook').

        Returns:
            bool: True if manual login successful, False otherwise.
        """
        attempts = 0

        while attempts < self.max_attempts:
            input(f"🔐 Please complete the login for {platform.capitalize()} in the browser, then press Enter when done... ")

            if check_func(driver):
                msg = f"✅ {platform.capitalize()} login detected."
                self.logger.info(msg)
                write_json_log(platform, "successful", tags=["manual_login"])
                self.save_cookies(driver, platform)
                return True
            else:
                msg = f"⚠️ {platform.capitalize()} login not detected. Attempt {attempts + 1}/{self.max_attempts}."
                self.logger.warning(msg)
                write_json_log(platform, "failed", tags=["manual_login_attempt"], ai_output=msg)
                attempts += 1

        msg = f"🚨 Maximum manual login attempts reached for {platform.capitalize()}."
        self.logger.error(msg)
        write_json_log(platform, "failed", tags=["manual_login"], ai_output=msg)
        return False
