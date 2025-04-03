import time
from typing import Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from .BasePlatformLoginService import BasePlatformLoginService

class DiscordLoginService(BasePlatformLoginService):
    """
    Discord-specific implementation of the platform login service.
    Handles Discord authentication using Selenium WebDriver.
    """

    DISCORD_LOGIN_URL = "https://discord.com/login"
    DISCORD_HOME_URL = "https://discord.com/channels/@me"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._token = None
        self._email = None

    @property
    def platform_name(self) -> str:
        return "Discord"

    def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connect to Discord using provided credentials.

        Args:
            credentials: Dict containing 'email' and 'password' or 'token'

        Returns:
            bool: True if connection successful, False otherwise
        """
        if not self.driver:
            self._log_error("WebDriver not initialized")
            return False

        try:
            if 'token' in credentials:
                return self._login_with_token(credentials['token'])
            elif 'email' in credentials and 'password' in credentials:
                return self._login_with_credentials(credentials['email'], credentials['password'])
            else:
                self._log_error("Invalid credentials provided")
                return False

        except Exception as e:
            self._log_error(f"Error connecting to Discord: {str(e)}")
            return False

    def disconnect(self) -> bool:
        """
        Disconnect from Discord.

        Returns:
            bool: True if disconnection successful, False otherwise
        """
        if not self.is_connected:
            return True

        try:
            self.driver.delete_all_cookies()
            self.driver.get("about:blank")
            self._token = None
            self._email = None
            self._update_connection_state(False)
            return True
        except Exception as e:
            self._log_error(f"Error disconnecting from Discord: {str(e)}")
            return False

    def test_connection(self) -> bool:
        """
        Test if the current Discord connection is valid.

        Returns:
            bool: True if connection is valid, False otherwise
        """
        if not self.driver:
            return False

        try:
            self.driver.get(self.DISCORD_HOME_URL)
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='privateChannels-']"))
            )
            return True
        except (TimeoutException, WebDriverException):
            return False

    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get the current Discord connection status.

        Returns:
            Dict containing connection status information
        """
        status = super().get_connection_status()
        if self.is_connected:
            status["session_data"] = {
                "token": self._token,
                "email": self._email
            }
        return status

    def _login_with_token(self, token: str) -> bool:
        """
        Login to Discord using an authentication token.

        Args:
            token: Discord authentication token

        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            self.driver.get("https://discord.com")
            script = f'''
                function login(token) {{
                    setInterval(() => document.body.appendChild(document.createElement('iframe'))
                        .contentWindow.localStorage.token = `"${{token}}"`, 50);
                    setTimeout(() => location.reload(), 500);
                }}
                login("{token}");
            '''
            self.driver.execute_script(script)
            time.sleep(5)  # Wait for the reload

            if self.test_connection():
                self._token = token
                self._update_connection_state(True)
                return True
            return False

        except Exception as e:
            self._log_error(f"Error logging in with token: {str(e)}")
            return False

    def _login_with_credentials(self, email: str, password: str) -> bool:
        """
        Login to Discord using email and password.

        Args:
            email: Discord account email
            password: Discord account password

        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            self.driver.get(self.DISCORD_LOGIN_URL)
            
            # Wait for and fill in email field
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            email_field.send_keys(email)

            # Fill in password field
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.send_keys(password)

            # Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()

            # Wait for successful login
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='privateChannels-']"))
                )
                self._email = email
                self._update_connection_state(True)
                return True
            except TimeoutException:
                self._log_error("Login timed out - check credentials")
                return False

        except Exception as e:
            self._log_error(f"Error logging in with credentials: {str(e)}")
            return False 