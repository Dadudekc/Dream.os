import os
import sys
import time
import unittest
import logging

# Ensure the parent directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.DriverManager import DriverManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DriverManagerTest")

class TestEnhancedDriverManager(unittest.TestCase):
    
    def setUp(self):
        """Set up the test environment."""
        self.driver_manager = DriverManager(
            headless=True,  # Use headless for CI/CD testing
            undetected_mode=False,  # Use regular mode for simplicity in tests
            timeout=10
        )
        
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self, 'driver_manager'):
            self.driver_manager.shutdown_driver()
            
    def test_singleton_pattern(self):
        """Test that the driver manager follows the singleton pattern."""
        second_manager = DriverManager()
        self.assertIs(self.driver_manager, second_manager)
        
    def test_driver_initialization(self):
        """Test that the driver can be initialized."""
        driver = self.driver_manager.get_driver()
        self.assertIsNotNone(driver)
        
    def test_driver_navigation(self):
        """Test basic navigation in the browser."""
        driver = self.driver_manager.get_driver()
        driver.get("https://www.google.com")
        self.assertIn("Google", driver.title)
        
    def test_cookie_save_load(self):
        """Test cookie saving and loading."""
        # Skip if no cookie file is configured
        if not self.driver_manager.cookie_file:
            self.driver_manager.cookie_file = "test_cookies.pkl"
            
        # Navigate to a site and set a test cookie
        driver = self.driver_manager.get_driver()
        driver.get("https://www.example.com")
        driver.add_cookie({"name": "test_cookie", "value": "test_value", "domain": ".example.com"})
        
        # Save cookies
        result = self.driver_manager.save_cookies()
        self.assertTrue(result)
        
        # Clear cookies
        driver.delete_all_cookies()
        
        # Load cookies
        result = self.driver_manager.load_cookies()
        self.assertTrue(result)
        
        # Check if cookie was loaded
        cookies = driver.get_cookies()
        self.assertTrue(any(cookie["name"] == "test_cookie" for cookie in cookies))
        
    def test_wait_functions(self):
        """Test the wait functions."""
        driver = self.driver_manager.get_driver()
        driver.get("https://www.google.com")
        
        # Test wait_and_find_element
        search_box = self.driver_manager.wait_and_find_element("name", "q")
        self.assertIsNotNone(search_box)
        
        # Test wait_for_url_change
        current_url = driver.current_url
        search_box.send_keys("test\n")  # Search for 'test'
        result = self.driver_manager.wait_for_url_change(current_url)
        self.assertTrue(result)
        
def run_tests():
    """Run the tests directly."""
    logger.info("Starting enhanced DriverManager tests...")
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEnhancedDriverManager)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return result.wasSuccessful()
    
if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 