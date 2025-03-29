import os
import sys
import shutil
import zipfile
import requests
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_chrome_version():
    """Try to get the Chrome version from the registry on Windows"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Google\Chrome\BLBeacon')
        value, _ = winreg.QueryValueEx(key, 'version')
        return value.split('.')[0]  # Return major version
    except Exception as e:
        logger.warning(f"Could not determine Chrome version from registry: {e}")
        # Default to latest version
        return None

def download_chromedriver(version=None):
    """Download ChromeDriver from the Chrome for Testing repository"""
    base_url = "https://storage.googleapis.com/chrome-for-testing-public"
    
    if version:
        # Use specific version
        logger.info(f"Looking for ChromeDriver compatible with Chrome version {version}")
        # For simplicity, we're using a known version that works
        version_url = f"{base_url}/LATEST_RELEASE_{version}"
        try:
            response = requests.get(version_url)
            if response.status_code == 200:
                driver_version = response.text.strip()
                logger.info(f"Found ChromeDriver version {driver_version} for Chrome {version}")
            else:
                logger.warning(f"Could not find specific ChromeDriver for version {version}, using latest")
                driver_version = None
        except Exception as e:
            logger.warning(f"Error fetching specific ChromeDriver version: {e}")
            driver_version = None
    else:
        driver_version = None
    
    # If we couldn't get a specific version, use latest
    if not driver_version:
        try:
            latest_url = f"{base_url}/LATEST_RELEASE"
            response = requests.get(latest_url)
            if response.status_code == 200:
                driver_version = response.text.strip()
                logger.info(f"Using latest ChromeDriver version: {driver_version}")
            else:
                logger.error("Failed to get latest ChromeDriver version")
                # Use a known good version as fallback
                driver_version = "114.0.5735.90"
                logger.info(f"Using fallback ChromeDriver version: {driver_version}")
        except Exception as e:
            logger.error(f"Error fetching latest ChromeDriver version: {e}")
            # Use a known good version as fallback
            driver_version = "114.0.5735.90"
            logger.info(f"Using fallback ChromeDriver version: {driver_version}")
    
    # Set up paths
    download_dir = Path("drivers")
    download_dir.mkdir(exist_ok=True)
    
    # Download the ChromeDriver zip file
    zip_url = f"{base_url}/{driver_version}/win32/chromedriver-win32.zip"
    zip_path = download_dir / "chromedriver.zip"
    
    logger.info(f"Downloading ChromeDriver from {zip_url}")
    try:
        response = requests.get(zip_url, stream=True)
        if response.status_code == 200:
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"Downloaded ChromeDriver to {zip_path}")
        else:
            logger.error(f"Failed to download ChromeDriver: HTTP {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error downloading ChromeDriver: {e}")
        return None
    
    # Extract the zip file
    extract_dir = download_dir / f"chromedriver_{driver_version}"
    extract_dir.mkdir(exist_ok=True)
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        logger.info(f"Extracted ChromeDriver to {extract_dir}")
    except Exception as e:
        logger.error(f"Error extracting ChromeDriver: {e}")
        return None
    
    # Find the chromedriver.exe in the extracted files
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.lower() == "chromedriver.exe":
                driver_path = os.path.join(root, file)
                logger.info(f"Found ChromeDriver executable at {driver_path}")
                
                # Create a symlink or copy to a standard location
                final_path = download_dir / "chromedriver.exe"
                if os.path.exists(final_path):
                    os.remove(final_path)
                
                shutil.copy2(driver_path, final_path)
                logger.info(f"Copied ChromeDriver to {final_path}")
                
                # Update the config file
                update_config(str(final_path.absolute()))
                
                return str(final_path.absolute())
    
    logger.error("ChromeDriver executable not found in the extracted files")
    return None

def update_config(driver_path):
    """Update the config.py file with the new ChromeDriver path"""
    config_path = "config.py"
    if not os.path.exists(config_path):
        logger.error(f"Config file not found at {config_path}")
        return
    
    try:
        with open(config_path, 'r') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            if line.strip().startswith("CHROMEDRIVER_PATH = "):
                # Replace the line with the new path
                lines[i] = f'CHROMEDRIVER_PATH = r"{driver_path}"  # Use absolute path\n'
                break
        
        with open(config_path, 'w') as f:
            f.writelines(lines)
        
        logger.info(f"Updated ChromeDriver path in {config_path}")
    except Exception as e:
        logger.error(f"Error updating config file: {e}")

if __name__ == "__main__":
    chrome_version = get_chrome_version()
    driver_path = download_chromedriver(chrome_version)
    
    if driver_path:
        logger.info(f"✅ ChromeDriver setup complete. Path: {driver_path}")
        sys.exit(0)
    else:
        logger.error("❌ ChromeDriver setup failed.")
        sys.exit(1) 