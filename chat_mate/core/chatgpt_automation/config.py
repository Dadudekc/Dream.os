"""
Configuration module for the chatgpt automation package.
"""

import os
from pathlib import Path

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

class Config:
    """Configuration class for the chatgpt automation package."""
    
    @staticmethod
    def get_models_dir() -> Path:
        """Get the directory for storing model configurations.
        
        Returns:
            Path: Path to the models directory.
        """
        base_dir = Path(os.path.expanduser("~")) / ".chat_mate"
        if not base_dir.exists():
            os.makedirs(base_dir)
            
        models_dir = base_dir / "models"
        if not models_dir.exists():
            os.makedirs(models_dir)
        return models_dir
