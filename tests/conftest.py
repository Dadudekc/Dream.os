import pytest
from fastapi.testclient import TestClient
from main import app
from core.services.prompt_execution_service import UnifiedPromptService
from core.services.discord_service import DiscordService
import os
from datetime import datetime
from unittest.mock import MagicMock, Mock
import sys
from unittest import mock
from PyQt5.QtWidgets import QApplication
import asyncio
import discord

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'tests', 'mocks'))

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

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def mock_prompt_service(mocker):
    service = UnifiedPromptService()
    # Mock the DreamscapeService methods
    mocker.patch.object(service.dreamscape, 'execute_prompt')
    mocker.patch.object(service.dreamscape, 'execute_cycle')
    return service

@pytest.fixture
def mock_discord_service(mocker):
    service = DiscordService()
    return service

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
def setup_test_environment():
    """Setup test environment for all tests."""
    # Ensure test data directory exists
    os.makedirs(os.getenv("DATA_DIR", "./data"), exist_ok=True)
    yield
    # Cleanup after tests
    test_files = [
        "chat_history.json",
        "response_cache.json",
        "conversation_analytics.json",
        "prompt_templates.json",
        "post_history.json",
        "engagement_metrics.json",
        "post_analytics.json",
        "scheduled_tasks.json",
        "processed_comments.json",
        "member_interactions.json",
        "community_metrics.json",
        "ai_response_history.json"
    ]
    for file in test_files:
        file_path = os.path.join(os.getenv("DATA_DIR", "./data"), file)
        if os.path.exists(file_path):
            os.remove(file_path)

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

@pytest.fixture(scope='session')
def qapp():
    """Create a QApplication instance for all tests."""
    app = QApplication([])
    yield app
    app.quit()

@pytest.fixture
def mock_services():
    """Create mock services for testing."""
    services = {
        'dispatcher': mock.MagicMock(),
        'prompt_manager': mock.MagicMock(),
        'chat_manager': mock.MagicMock(),
        'response_handler': mock.MagicMock(),
        'memory_manager': mock.MagicMock(),
        'discord_manager': mock.MagicMock(),
        'ui_logic': mock.MagicMock(),
        'config_manager': mock.MagicMock(),
        'logger': mock.MagicMock()
    }
    
    # Configure chat manager
    services['chat_manager'].get_all_chat_titles.return_value = [
        {"title": "Project Alpha", "link": "https://chat.openai.com/1"},
        {"title": "System Beta", "link": "https://chat.openai.com/2"},
        {"title": "ChatGPT", "link": "https://chat.openai.com/3"},  # Should be excluded
    ]
    
    # Configure dreamscape service
    mock_dreamscape_service = mock.MagicMock()
    mock_dreamscape_service.send_context_to_chatgpt.return_value = True
    mock_dreamscape_service.schedule_context_updates.return_value = True
    services['ui_logic'].get_service.return_value = mock_dreamscape_service
    
    return services

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

@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    # Stop the loop before closing it
    if loop.is_running():
        loop.call_soon_threadsafe(loop.stop)
    
    # Only close if not running
    if not loop.is_running():
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