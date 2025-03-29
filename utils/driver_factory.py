import undetected_chromedriver as uc
from webdriver_manager.chrome import ChromeDriverManager
import os
import shutil
import logging

CACHED_DRIVER_PATH = os.path.join(os.path.dirname(__file__), "..", "drivers", "chromedriver.exe")
PROFILE_DIR = os.path.join(os.path.dirname(__file__), "..", "chrome_profile", "openai")

def create_driver(logger=None):
    logger = logger or logging.getLogger("create_driver")

    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    if PROFILE_DIR:
        options.add_argument(f"--user-data-dir={PROFILE_DIR}")

    if os.path.exists(CACHED_DRIVER_PATH):
        driver_path = CACHED_DRIVER_PATH
        logger.info(f"Using cached ChromeDriver: {driver_path}")
    else:
        logger.warning("No cached ChromeDriver found. Downloading latest...")
        driver_path = ChromeDriverManager().install()
        os.makedirs(os.path.dirname(CACHED_DRIVER_PATH), exist_ok=True)
        shutil.copyfile(driver_path, CACHED_DRIVER_PATH)
        driver_path = CACHED_DRIVER_PATH
        logger.info(f"Cached ChromeDriver at: {driver_path}")

    driver = uc.Chrome(options=options, driver_executable_path=driver_path)
    logger.info("Undetected Chrome driver initialized.")
    return driver
