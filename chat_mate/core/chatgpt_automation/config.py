import os

# ---------- CONFIGURATION ----------

# URLs and Files
CHATGPT_URL = "https://chat.openai.com/"
COOKIE_FILE = "chatgpt_cookies.json"

# Chrome Driver Path (adjust as needed)
CHROMEDRIVER_PATH = r"C:/Users/USER/Downloads/chromedriver-win64/chromedriver.exe"  # Use absolute path

# Headless browser mode
CHATGPT_HEADLESS = False

# Chrome Profile Directory
CURRENT_DIR = os.path.abspath(os.getcwd())
PROFILE_DIR = os.path.join(CURRENT_DIR, "chrome_profile", "openai")
os.makedirs(PROFILE_DIR, exist_ok=True)  # Ensure directory is created
