"""
PyQt5 GUI test fixtures for use with pytest.
"""

import os
import sys
import io
import pytest
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from unittest.mock import MagicMock

# Add application root to sys.path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Fix Unicode encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# Safe formatter for handling emoji encoding issues
class SafeFormatter(logging.Formatter):
    def format(self, record):
        try:
            return super().format(record)
        except UnicodeEncodeError:
            record.msg = record.msg.encode('ascii', 'ignore').decode('ascii')
            return super().format(record)

# Configure logging with safe formatter
logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
formatter = SafeFormatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@pytest.fixture(scope="session")
def qapp():
    """
    Fixture that creates a QApplication instance for the entire test session.
    """
    # Create QApplication only if it doesn't exist
    if not QApplication.instance():
        app = QApplication([])
    else:
        app = QApplication.instance()
    
    yield app


@pytest.fixture
def qtbot(qapp, monkeypatch):
    """
    Fixture for Qt testing with pytest-qt.
    If pytest-qt is not installed, this creates a simplified version.
    """
    try:
        from pytestqt.plugin import QtBot
        result = QtBot(qapp)
        yield result
    except ImportError:
        # Simple mock of qtbot if pytest-qt is not installed
        class MockQtBot:
            def __init__(self, app):
                self.app = app
            
            def addWidget(self, widget):
                """Add a widget to the bot's widgets list"""
                pass
            
            def waitExposed(self, widget, timeout=None):
                """Wait until widget is exposed/visible"""
                pass
            
            def wait(self, ms):
                """Wait for given milliseconds"""
                pass
                
            def waitUntil(self, callback, timeout=None):
                """Wait until callback returns True"""
                pass
                
            def mouseClick(self, widget, button=Qt.LeftButton, pos=None, delay=-1):
                """Simulate mouse click on widget"""
                pass
                
            def keyClick(self, widget, key, modifier=None, delay=-1):
                """Simulate key click on widget"""
                pass
        
        mock_bot = MockQtBot(qapp)
        yield mock_bot


@pytest.fixture
def mock_config_manager():
    """
    Fixture that provides a mock config manager for testing.
    """
    class MockConfigManager:
        def __init__(self):
            self.credentials = {}
            self.settings = {}
        
        def get_credentials(self):
            return self.credentials
            
        def get_settings(self):
            return self.settings
            
        def update_credentials(self, credentials):
            self.credentials.update(credentials)
            
        def update_settings(self, settings):
            self.settings.update(settings)
    
    return MockConfigManager()


@pytest.fixture
def mock_analytics_manager():
    """
    Fixture that provides a mock analytics manager for testing.
    """
    class MockAnalyticsManager:
        def __init__(self):
            self.data = {}
            
        def get_metrics(self, platform=None):
            return {"views": 1000, "engagement": 75.5, "followers": 500}
            
        def refresh_data(self):
            pass
    
    return MockAnalyticsManager()


@pytest.fixture
def mock_community_manager():
    """
    Fixture that provides a mock community manager for testing.
    """
    class MockCommunityManager:
        def __init__(self):
            self.platforms = ["Twitter", "Facebook", "LinkedIn", "Reddit"]
            
        def get_platforms(self):
            return self.platforms
            
        def post_content(self, platform, content):
            return True
            
        def get_members(self, platform=None):
            return [{"name": "Test User", "engagement_score": 85}]
    
    return MockCommunityManager()


@pytest.fixture
def mock_chat_manager():
    """
    Fixture that provides a mock chat manager for testing.
    """
    class MockChatManager:
        def __init__(self):
            self.history = []
            
        def send_message(self, message):
            self.history.append({"role": "user", "content": message})
            return "This is a mock response from the AI."
            
        def get_history(self):
            return self.history
    
    return MockChatManager()


@pytest.fixture
def mock_template_manager():
    """
    Fixture that provides a mock template manager for testing.
    """
    class MockTemplateManager:
        def __init__(self):
            self.templates = {
                "test_template": {
                    "name": "Test Template",
                    "description": "A test template",
                    "content": "Test content"
                }
            }
            self.templates_updated = MagicMock()
            
        def get_templates(self):
            return self.templates
            
        def add_template(self, template_id, template_data):
            self.templates[template_id] = template_data
            self.templates_updated.emit()
            
        def update_template(self, template_id, template_data):
            if template_id in self.templates:
                self.templates[template_id].update(template_data)
                self.templates_updated.emit()
            
        def delete_template(self, template_id):
            if template_id in self.templates:
                del self.templates[template_id]
                self.templates_updated.emit()
    
    return MockTemplateManager()


@pytest.fixture
def mock_chat_engine():
    """
    Fixture that provides a mock chat engine for testing.
    """
    class MockChatEngine:
        def __init__(self):
            self.responses = []
            
        def execute_prompt(self, prompt, **kwargs):
            response = f"Mock response for: {prompt}"
            self.responses.append(response)
            return response
            
        def get_response_history(self):
            return self.responses
    
    return MockChatEngine()


@pytest.fixture
def mock_driver_manager():
    """
    Fixture that provides a mock driver manager for testing.
    """
    class MockDriverManager:
        def __init__(self):
            self.is_running = False
            
        def start(self):
            self.is_running = True
            
        def stop(self):
            self.is_running = False
            
        def quit(self):
            self.is_running = False
            
        def execute_command(self, command):
            return f"Executed: {command}"
    
    return MockDriverManager() 