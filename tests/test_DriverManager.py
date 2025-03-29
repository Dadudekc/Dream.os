# tests/test_DriverManager.py

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure the core directory is in the path if needed
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

from core.DriverManager import DriverManager


class TestDriverManager(unittest.TestCase):
    """
    Basic unit tests for DriverManager class.
    """

    @patch("undetected_chromedriver.Chrome")
    @patch("os.path.exists")
    @patch("shutil.copyfile")
    @patch("webdriver_manager.chrome.ChromeDriverManager.install")
    def test_driver_initialization_with_cache(self, mock_install, mock_copyfile, mock_exists, mock_uc_chrome):
        """
        Test initialization when driver is already cached.
        """
        # Setup
        mock_exists.return_value = True
        driver_manager = DriverManager(profile_dir="fake_profile", driver_cache_dir="fake_cache", headless=True)

        # Action
        driver = driver_manager.get_driver()

        # Assert
        mock_install.assert_not_called()
        mock_copyfile.assert_not_called()
        mock_uc_chrome.assert_called_once()

    @patch("undetected_chromedriver.Chrome")
    @patch("core.DriverManager.os.path.exists")
    @patch("shutil.copyfile")
    @patch("core.DriverManager.DriverManager._download_driver_if_needed")
    def test_driver_download_when_cache_missing(self, mock_download_driver, mock_copyfile, mock_exists, mock_uc_chrome):
        """
        Test driver download and caching when no cache is found.
        """
        # Setup
        # First check is for cache file, second is for cookie dir, third is for profile dir
        mock_exists.side_effect = [False, True, True]  # Simplified to just handle the essential checks
        mock_download_driver.return_value = "path/to/downloaded/driver"

        # Create a new DriverManager instance
        driver_manager = DriverManager(profile_dir="fake_profile", driver_cache_dir="fake_cache", headless=False)

        # Action
        driver = driver_manager.get_driver()

        # Assert
        mock_download_driver.assert_called_once()
        mock_uc_chrome.assert_called_once()
        self.assertIsNotNone(driver)

    @patch("undetected_chromedriver.Chrome")
    def test_quit_driver(self, mock_uc_chrome):
        """
        Test quitting the driver shuts down session.
        """
        # Setup
        mock_driver_instance = MagicMock()
        mock_uc_chrome.return_value = mock_driver_instance

        driver_manager = DriverManager()
        driver = driver_manager.get_driver()

        # Action
        driver_manager.quit_driver()

        # Assert
        mock_driver_instance.quit.assert_called_once()
        self.assertIsNone(driver_manager.driver)


if __name__ == "__main__":
    unittest.main()
