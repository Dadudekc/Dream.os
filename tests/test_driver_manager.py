import unittest
from unittest.mock import patch, MagicMock, mock_open
import os

from core.DriverManager import DriverManager


class TestDriverManager(unittest.TestCase):
    def setUp(self):
        # Patch logger to suppress actual logging during tests
        patcher_logger = patch('core.DriverManager.logger')
        self.mock_logger = patcher_logger.start()
        self.addCleanup(patcher_logger.stop)

        # Patch os.makedirs
        patcher_makedirs = patch('core.DriverManager.os.makedirs')
        self.mock_makedirs = patcher_makedirs.start()
        self.addCleanup(patcher_makedirs.stop)

        # Patch time.sleep to speed up tests
        patcher_sleep = patch('core.DriverManager.time.sleep')
        self.mock_sleep = patcher_sleep.start()
        self.addCleanup(patcher_sleep.stop)

        # Dummy paths
        self.dummy_profile_dir = '/fake/profile/dir'
        self.dummy_cache_dir = '/fake/driver/cache'
        self.dummy_cookie_file = '/fake/cookies/file.pkl'

    # ---------- INIT ----------
    def test_init_sets_directories(self):
        manager = DriverManager(
            profile_dir=self.dummy_profile_dir,
            driver_cache_dir=self.dummy_cache_dir,
            cookie_file=self.dummy_cookie_file,
            headless=True,
            mobile_emulation=True
        )

        self.assertEqual(manager.profile_dir, self.dummy_profile_dir)
        self.assertEqual(manager.driver_cache_dir, self.dummy_cache_dir)
        self.assertEqual(manager.cookie_file, self.dummy_cookie_file)
        self.assertTrue(manager.headless)
        self.assertTrue(manager.mobile_emulation)

    # ---------- DRIVER SETUP ----------
    @patch('core.DriverManager.ChromeDriverManager')
    @patch('core.DriverManager.shutil.copyfile')
    @patch('core.DriverManager.os.path.exists')
    def test_download_driver_if_needed_downloads_when_missing(self, mock_exists, mock_copyfile, mock_chromedriver_manager):
        mock_exists.return_value = False
        mock_chromedriver_manager.return_value.install.return_value = "/downloaded/driver"

        manager = DriverManager(driver_cache_dir=self.dummy_cache_dir)
        downloaded_driver = manager._download_driver_if_needed()

        mock_copyfile.assert_called_once_with("/downloaded/driver", downloaded_driver)
        self.assertEqual(downloaded_driver, os.path.join(self.dummy_cache_dir, "chromedriver.exe"))

    @patch('core.DriverManager.os.path.exists')
    def test_download_driver_if_needed_uses_cache(self, mock_exists):
        mock_exists.return_value = True

        manager = DriverManager(driver_cache_dir=self.dummy_cache_dir)
        cached_driver = manager._download_driver_if_needed()

        self.assertEqual(cached_driver, os.path.join(self.dummy_cache_dir, "chromedriver.exe"))

    @patch('core.DriverManager.uc.Chrome')
    @patch('core.DriverManager.ChromeService')
    @patch('core.DriverManager.DriverManager._download_driver_if_needed')
    def test_get_driver_initializes_driver(self, mock_download, mock_service, mock_chrome):
        mock_download.return_value = "/fake/driver/path"

        manager = DriverManager(headless=False)
        driver = manager.get_driver(force_new=True)

        mock_chrome.assert_called_once()
        self.assertEqual(driver, mock_chrome.return_value)

    @patch('core.DriverManager.uc.Chrome')
    @patch('core.DriverManager.ChromeService')
    @patch('core.DriverManager.DriverManager._download_driver_if_needed')
    def test_get_driver_returns_existing(self, mock_download, mock_service, mock_chrome):
        mock_download.return_value = "/fake/driver/path"

        manager = DriverManager(headless=False)
        first_driver = manager.get_driver(force_new=True)

        # Should return existing driver without re-initialization
        second_driver = manager.get_driver(force_new=False)
        self.assertEqual(first_driver, second_driver)

    @patch('core.DriverManager.shutil.rmtree')
    def test_quit_driver_with_temp_profile(self, mock_rmtree):
        manager = DriverManager()
        mock_driver = MagicMock()
        manager.driver = mock_driver
        manager.temp_profile = "/fake/temp/profile"

        manager.quit_driver()

        mock_driver.quit.assert_called_once()
        mock_rmtree.assert_called_once_with(manager.temp_profile)
        self.assertIsNone(manager.driver)
        self.assertIsNone(manager.temp_profile)

    def test_quit_driver_without_driver(self):
        manager = DriverManager()
        manager.quit_driver()  # Should not raise errors
        self.assertIsNone(manager.driver)

    # ---------- COOKIE HANDLING ----------
    @patch('core.DriverManager.pickle.dump')
    @patch('core.DriverManager.open', new_callable=mock_open)
    def test_save_cookies_success(self, mock_file, mock_pickle_dump):
        manager = DriverManager()
        mock_driver = MagicMock()
        mock_driver.get_cookies.return_value = [{"name": "test_cookie"}]
        manager.driver = mock_driver

        manager.save_cookies()

        mock_file.assert_called_once_with(manager.cookie_file, "wb")
        mock_pickle_dump.assert_called_once_with(mock_driver.get_cookies.return_value, mock_file.return_value)

    def test_save_cookies_no_driver(self):
        manager = DriverManager()
        manager.driver = None

        manager.save_cookies()  # Should warn and exit without exception

    @patch('core.DriverManager.pickle.load')
    @patch('core.DriverManager.open', new_callable=mock_open)
    @patch('core.DriverManager.os.path.exists')
    def test_load_cookies_success(self, mock_exists, mock_file, mock_pickle_load):
        mock_exists.return_value = True
        mock_pickle_load.return_value = [{"name": "test_cookie"}]

        manager = DriverManager()
        manager.driver = MagicMock()

        result = manager.load_cookies()

        self.assertTrue(result)
        manager.driver.add_cookie.assert_called()
        manager.driver.refresh.assert_called()

    @patch('core.DriverManager.os.path.exists')
    def test_load_cookies_no_driver(self, mock_exists):
        manager = DriverManager()
        manager.driver = None

        result = manager.load_cookies()

        self.assertFalse(result)

    @patch('core.DriverManager.os.path.exists')
    def test_load_cookies_no_file(self, mock_exists):
        mock_exists.return_value = False

        manager = DriverManager()
        manager.driver = MagicMock()

        result = manager.load_cookies()

        self.assertFalse(result)

    # ---------- LOGIN CHECK ----------
    @patch('core.DriverManager.WebDriverWait')
    def test_is_logged_in_success(self, mock_wait):
        mock_wait.return_value.until.return_value = True

        manager = DriverManager()
        manager.driver = MagicMock()

        result = manager.is_logged_in()

        self.assertTrue(result)

    @patch('core.DriverManager.WebDriverWait')
    def test_is_logged_in_failure(self, mock_wait):
        mock_wait.return_value.until.side_effect = Exception("Not found")

        manager = DriverManager()
        manager.driver = MagicMock()

        result = manager.is_logged_in(retries=1)

        self.assertFalse(result)

    def test_is_logged_in_no_driver(self):
        manager = DriverManager()
        manager.driver = None

        result = manager.is_logged_in()

        self.assertFalse(result)

    # ---------- SCROLLING ----------
    def test_scroll_into_view_success(self):
        manager = DriverManager()
        manager.driver = MagicMock()

        element = MagicMock()
        manager.scroll_into_view(element)

        manager.driver.execute_script.assert_called_with(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element
        )

    def test_scroll_into_view_no_driver(self):
        manager = DriverManager()
        manager.driver = None

        manager.scroll_into_view(MagicMock())  # Should warn and exit without exception

    def test_manual_scroll_success(self):
        manager = DriverManager()
        manager.driver = MagicMock()

        # Simulate scroll height changes
        manager.driver.execute_script.side_effect = [100, 200, 300, 300]

        manager.manual_scroll(scroll_pause_time=0.1, max_scrolls=3)

        self.assertGreaterEqual(manager.driver.execute_script.call_count, 4)

    def test_manual_scroll_no_driver(self):
        manager = DriverManager()
        manager.driver = None

        manager.manual_scroll()  # Should warn and exit without exception


if __name__ == "__main__":
    unittest.main()
