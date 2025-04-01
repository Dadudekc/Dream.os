import os
import pytest
import platform
from pathlib import Path
from unittest.mock import patch, MagicMock
from core.chatgpt_automation.OpenAIClient import OpenAIClient

@pytest.fixture
def temp_profile_dir(tmp_path):
    profile_dir = tmp_path / "chrome_profile"
    profile_dir.mkdir()
    return str(profile_dir)

@pytest.fixture
def mock_config():
    return {
        "default_model": "gpt-4o-mini",
        "auto_commit": True,
        "auto_test": True,
        "debug_mode": False,
        "chrome_driver": {
            "auto_detect": True,
            "fallback_paths": [
                "drivers/chromedriver",
                "chromedriver/chromedriver"
            ]
        }
    }

def test_init_paths(temp_profile_dir):
    client = OpenAIClient(profile_dir=temp_profile_dir)
    assert isinstance(client.profile_dir, str)
    assert isinstance(client.COOKIE_DIR, str)
    assert isinstance(client.COOKIE_FILE, str)
    assert isinstance(client.CONFIG_FILE, str)

def test_config_loading(temp_profile_dir, mock_config):
    config_path = Path(os.getcwd()) / "config" / "command_config.json"
    os.makedirs(config_path.parent, exist_ok=True)
    
    with open(config_path, 'w') as f:
        import json
        json.dump(mock_config, f)

    client = OpenAIClient(profile_dir=temp_profile_dir)
    assert client.config == mock_config

@patch('undetected_chromedriver.Chrome')
def test_driver_initialization(mock_chrome, temp_profile_dir):
    mock_chrome.return_value = MagicMock()
    client = OpenAIClient(profile_dir=temp_profile_dir)
    assert client.driver is not None

@patch('undetected_chromedriver.Chrome')
def test_fallback_paths(mock_chrome, temp_profile_dir):
    # Simulate first attempt failing
    mock_chrome.side_effect = [Exception("First attempt failed"), MagicMock()]
    
    client = OpenAIClient(profile_dir=temp_profile_dir)
    assert client.driver is not None

def test_platform_specific_paths(temp_profile_dir):
    client = OpenAIClient(profile_dir=temp_profile_dir)
    
    # Verify paths are properly formatted for the current platform
    assert os.path.sep in client.profile_dir
    assert os.path.sep in client.COOKIE_DIR
    assert os.path.sep in client.COOKIE_FILE
    
    # Verify no Windows-specific path separators on non-Windows platforms
    if platform.system() != "Windows":
        assert "\\" not in client.profile_dir
        assert "\\" not in client.COOKIE_DIR
        assert "\\" not in client.COOKIE_FILE 
