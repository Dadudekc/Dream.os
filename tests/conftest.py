"""
Test configuration and fixtures for pytest.
"""

import os
import sys
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, Mock, AsyncMock
from datetime import datetime

import pytest
from PyQt5.QtWidgets import QApplication
from fastapi import FastAPI
import asyncio
from fastapi.testclient import TestClient

# Get the absolute path to the project root
project_root = str(Path(__file__).resolve().parent.parent)

# Add the project root to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add the config directory to the Python path
config_path = os.path.join(project_root, 'config')
if config_path not in sys.path:
    sys.path.insert(0, config_path)

# Create data directory if it doesn't exist
os.makedirs(os.getenv("DATA_DIR", "./data"), exist_ok=True)

# Mock GUI modules
mock_gui = mock.MagicMock()
mock_gui_helpers = mock.MagicMock()
mock_gui_helpers.GuiHelpers = mock.MagicMock()

sys.modules['GUI'] = mock_gui
sys.modules['GUI.GuiHelpers'] = mock_gui_helpers

# Mock chatgpt_automation modules
mock_file_browser = mock.MagicMock()
mock_file_browser.FileBrowserWidget = mock.MagicMock()

sys.modules['chatgpt_automation'] = mock.MagicMock()
sys.modules['chatgpt_automation.views'] = mock.MagicMock()
sys.modules['chatgpt_automation.views.file_browser_widget'] = mock_file_browser

# Mock the cursor_dispatcher module
class MockCursorDispatcher:
    def __init__(self):
        self.connected = False
        
    def connect(self):
        self.connected = True
        
    def disconnect(self):
        self.connected = False
        
    def send_message(self, message):
        return True

sys.modules['cursor_dispatcher'] = Mock()
sys.modules['cursor_dispatcher'].CursorDispatcher = MockCursorDispatcher

# Create a mock FastAPI app
app = FastAPI()

# Mock the services
class MockUnifiedPromptService:
    def __init__(self):
        self.dreamscape = MagicMock()
        self.dreamscape.execute_prompt = MagicMock()
        self.dreamscape.execute_cycle = MagicMock()

class MockDiscordService:
    def __init__(self):
        pass

@pytest.fixture
def test_client():
    from fastapi.testclient import TestClient
    return TestClient(app)

@pytest.fixture
def mock_prompt_service():
    return MockUnifiedPromptService()

@pytest.fixture
def mock_discord_service():
    return MockDiscordService()

@pytest.fixture
def sample_prompt_request():
    return {
        "prompt_text": "Test prompt",
        "context": {"test": "context"},
        "model": "gpt-4",
        "temperature": 0.7
    }

@pytest.fixture
def sample_cycle_request():
    return {
        "initial_prompt": "Test cycle",
        "max_iterations": 3,
        "stop_condition": "test condition",
        "cycle_config": {"test": "config"}
    }

@pytest.fixture
def sample_bot_config():
    return {
        "token": "test_token",
        "channel_id": "123456789",
        "prefix": "!",
        "allowed_roles": ["admin"],
        "auto_responses": True
    }

@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment before each test."""
    # Set up any environment variables or configurations needed for tests
    os.environ['TESTING'] = 'true'
    yield
    # Clean up after tests
    if 'TESTING' in os.environ:
        del os.environ['TESTING']

@pytest.fixture
def mock_openai():
    """Mock OpenAI for testing."""
    mock = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Test response"
    mock.ChatCompletion.create.return_value = mock_response
    return mock

@pytest.fixture
def test_video_data():
    """Common test video data."""
    return {
        "title": "Test Video",
        "description": "Test description",
        "video_id": "test123",
        "tags": ["test", "video"],
        "thumbnail_url": "https://example.com/thumb.jpg",
        "platform": "youtube",
        "timestamp": datetime.now().isoformat()
    }

@pytest.fixture
def test_comment_data():
    """Common test comment data."""
    return {
        "id": "comment123",
        "content": "Great video! How did you make this?",
        "post_id": "post123",
        "author": "test_user",
        "timestamp": datetime.now().isoformat(),
        "platform": "wordpress"
    }

@pytest.fixture
def test_context_data():
    """Common test context data."""
    return {
        "video_title": "Test Video",
        "channel_name": "TestChannel",
        "previous_interactions": [],
        "user_type": "new_user",
        "platform": "youtube"
    }

@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

@pytest.fixture
def mock_services():
    """Create mock services for components."""
    # Use MagicMock/AsyncMock for services
    ui_logic_mock = MagicMock()
    # Make the get_service method return an AsyncMock so its methods can be awaited
    ui_logic_mock.get_service.return_value = AsyncMock()

    return {
        'dispatcher': MagicMock(),
        'prompt_manager': MagicMock(),
        'chat_manager': MagicMock(),
        'response_handler': MagicMock(),
        'memory_manager': MagicMock(),
        'discord_manager': MagicMock(),
        'ui_logic': ui_logic_mock, # Use the configured mock
        'config_manager': MagicMock(),
        'logger': MagicMock()
    }

@pytest.fixture
def test_env(tmp_path):
    """Create a test environment with necessary files and directories."""
    test_dir = tmp_path / "test_outputs" / "dreamscape"
    test_dir.mkdir(parents=True)
    
    # Create test episodes
    episodes = [
        {
            "filename": "20240101_Episode_#1_Test.txt",
            "content": "Test episode 1 content"
        },
        {
            "filename": "20240102_DS-001_Another_Test.txt",
            "content": "Test episode 2 content"
        }
    ]
    
    for episode in episodes:
        episode_file = test_dir / episode["filename"]
        episode_file.write_text(episode["content"])
    
    return test_dir 

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def mock_discord_client():
    client = discord.Client(intents=discord.Intents.all())
    yield client
    await client.close()

@pytest.fixture
def mock_chat_manager():
    chat_manager = Mock()
    chat_manager.get_all_chat_titles.return_value = [
        {"title": "Project Alpha", "link": "https://chat.openai.com/1"},
        {"title": "System Beta", "link": "https://chat.openai.com/2"},
        {"title": "ChatGPT", "link": "https://chat.openai.com/3"},  # Should be excluded
    ]
    return chat_manager

@pytest.fixture
def mock_response_handler():
    return Mock()

@pytest.fixture
def mock_discord_manager():
    return Mock() 
