import pytest
import os
import sys
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the project root to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

# We'll test these components
try:
    from interfaces.pyqt.tabs.dreamscape_generation.DreamscapeGenerationTab import DreamscapeGenerationTab
    from interfaces.pyqt.tabs.dreamscape_generation.UIManager import UIManager
    from interfaces.pyqt.tabs.dreamscape_generation.ContextManager import ContextManager
    from interfaces.pyqt.tabs.dreamscape_generation.ServiceInitializer import ServiceInitializer
    from core.services.dreamscape.engine import DreamscapeGenerationService
    DREAMSCAPE_TAB_AVAILABLE = True
except ImportError:
    DREAMSCAPE_TAB_AVAILABLE = False
    print("Warning: Dreamscape tab components not found. Some tests will be skipped.")

# Create QApplication instance for tests
@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

# Mock services
@pytest.fixture
def mock_services():
    """Create a dictionary of mock services."""
    return {
        'chat_manager': MagicMock(),
        'dreamscape_service': MagicMock(),
        'context_synthesizer': MagicMock(),
        'template_manager': MagicMock(),
        'episode_generator': MagicMock(),
        'ui_manager': MagicMock(),
        'logger': MagicMock()
    }

@pytest.fixture
def mock_chat_data():
    """Create mock chat history data."""
    return [
        {
            'title': 'Test Chat 1',
            'timestamp': '2025-03-30T12:00:00Z',
            'messages': [
                {'role': 'user', 'content': 'Hello, how are you?'},
                {'role': 'assistant', 'content': 'I am well, thank you!'}
            ]
        },
        {
            'title': 'Test Chat 2',
            'timestamp': '2025-03-30T13:00:00Z',
            'messages': [
                {'role': 'user', 'content': 'Tell me about dreamscapes'},
                {'role': 'assistant', 'content': 'Dreamscapes are narrative experiences...'}
            ]
        }
    ]

@pytest.fixture
def mock_episode_content():
    """Create mock episode content."""
    return """# Digital Dreamscape: Episode 1
    
## Setting
A beautiful coastal town with towering cliffs.

## Characters
- **Alex**: The protagonist, a curious explorer.
- **Maya**: A mysterious guide with knowledge of the dreamscape.

## Plot
Alex discovers a hidden cave that leads to another dimension...
"""

# Skip tests if components are not available
pytestmark = pytest.mark.skipif(
    not DREAMSCAPE_TAB_AVAILABLE,
    reason="Dreamscape tab components not available"
)

# Patch the ServiceInitializer.initialize_all() method
@pytest.fixture
def patched_service_initializer(mock_services):
    """Patch the ServiceInitializer to return mock services."""
    with patch('interfaces.pyqt.tabs.dreamscape_generation.ServiceInitializer.ServiceInitializer.initialize_all') as mock_init:
        mock_init.return_value = mock_services
        yield mock_init

@pytest.fixture
def dreamscape_tab(qapp, patched_service_initializer, tmp_path):
    """Create a DreamscapeGenerationTab instance for testing."""
    # Create a temporary output directory
    output_dir = tmp_path / "dreamscape"
    output_dir.mkdir(exist_ok=True)
    
    # Create the tab
    tab = DreamscapeGenerationTab()
    
    # Set the output directory
    tab.output_dir = output_dir
    
    return tab

# Unit tests begin here

def test_tab_initialization(dreamscape_tab, patched_service_initializer):
    """Test that the tab initializes properly with all required components."""
    # Service initializer should be called once
    patched_service_initializer.assert_called_once()
    
    # Verify UI components are created
    assert hasattr(dreamscape_tab, 'chat_combo')
    assert hasattr(dreamscape_tab, 'episode_list')
    assert hasattr(dreamscape_tab, 'episode_viewer')
    assert hasattr(dreamscape_tab, 'progress_bar')
    assert hasattr(dreamscape_tab, 'status_label')

def test_load_available_chats(dreamscape_tab, mock_services, mock_chat_data):
    """Test loading available chats into the dropdown."""
    # Skip if components are not available
    if not hasattr(dreamscape_tab, 'chat_combo') or not hasattr(dreamscape_tab, 'chat_manager'):
        pytest.skip("Required components not available")
    
    # Setup mock
    mock_services['chat_manager'].get_all_chat_titles.return_value = mock_chat_data
    dreamscape_tab.chat_manager = mock_services['chat_manager']
    
    # Call the method
    dreamscape_tab.load_available_chats()
    
    # Verify results
    assert dreamscape_tab.chat_combo.count() == 2
    assert dreamscape_tab.chat_combo.itemText(0) == 'Test Chat 1'
    assert dreamscape_tab.chat_combo.itemText(1) == 'Test Chat 2'
    assert "Loaded 2 chats" in dreamscape_tab.status_label.text()

def test_load_episode_list(dreamscape_tab, tmp_path):
    """Test loading the episode list from the output directory."""
    # Skip if components are not available
    if not hasattr(dreamscape_tab, 'episode_list'):
        pytest.skip("Required components not available")
    
    # Create test episode files
    output_dir = tmp_path / "dreamscape"
    test_episodes = [
        output_dir / "episode_1.md",
        output_dir / "episode_2.md"
    ]
    
    for i, episode in enumerate(test_episodes):
        episode.write_text(f"Test episode {i+1} content")
    
    # Call the method
    dreamscape_tab.load_episode_list()
    
    # Verify results
    assert dreamscape_tab.episode_list.count() == 2
    # Episodes should be sorted most recent first, but since they're created
    # virtually at the same time, we can't predict the order reliably
    assert "episode_" in dreamscape_tab.episode_list.item(0).text()
    assert "episode_" in dreamscape_tab.episode_list.item(1).text()

def test_load_selected_episode(dreamscape_tab, tmp_path, mock_episode_content):
    """Test loading a selected episode's content into the viewer."""
    # Skip if components are not available
    if not hasattr(dreamscape_tab, 'episode_list') or not hasattr(dreamscape_tab, 'episode_viewer'):
        pytest.skip("Required components not available")
    
    # Create a test episode file
    output_dir = tmp_path / "dreamscape"
    test_episode = output_dir / "test_episode.md"
    test_episode.write_text(mock_episode_content)
    
    # Create and set up a list item
    dreamscape_tab.episode_list.clear()
    from PyQt5.QtWidgets import QListWidgetItem
    item = QListWidgetItem("test_episode.md")
    item.setData(Qt.UserRole, str(test_episode))
    dreamscape_tab.episode_list.addItem(item)
    
    # Select the item - this would normally trigger load_selected_episode
    # but we'll call it directly
    current = dreamscape_tab.episode_list.item(0)
    dreamscape_tab.load_selected_episode(current, None)
    
    # Verify the content is loaded
    assert "Digital Dreamscape: Episode 1" in dreamscape_tab.episode_viewer.toPlainText()
    assert "Alex discovers a hidden cave" in dreamscape_tab.episode_viewer.toPlainText()

def test_update_status(dreamscape_tab):
    """Test the status update functionality."""
    # Skip if components are not available
    if not hasattr(dreamscape_tab, 'status_label'):
        pytest.skip("Required components not available")
    
    # Call the method
    dreamscape_tab.update_status("Test status message")
    
    # Verify the label is updated
    assert dreamscape_tab.status_label.text() == "Test status message"

def test_generate_episode_no_chat_selected(dreamscape_tab):
    """Test episode generation with no chat selected."""
    # Skip if components are not available
    if not hasattr(dreamscape_tab, 'chat_combo') or not hasattr(dreamscape_tab, 'progress_bar'):
        pytest.skip("Required components not available")
    
    # Setup
    dreamscape_tab.chat_combo.clear()  # Ensure no chat is selected
    
    # Call the method
    dreamscape_tab.generate_episode_from_selected_chat()
    
    # Verify the status message
    assert "No chat selected" in dreamscape_tab.status_label.text()
    assert dreamscape_tab.progress_bar.value() == 0

def test_progress_bar_updates(dreamscape_tab):
    """Test that the progress bar updates correctly."""
    # Skip if components are not available
    if not hasattr(dreamscape_tab, 'progress_bar'):
        pytest.skip("Required components not available")
    
    # Start with zero
    dreamscape_tab.progress_bar.setValue(0)
    
    # Update to 50%
    dreamscape_tab.progress_bar.setValue(50)
    assert dreamscape_tab.progress_bar.value() == 50
    
    # Update to 100%
    dreamscape_tab.progress_bar.setValue(100)
    assert dreamscape_tab.progress_bar.value() == 100

if __name__ == "__main__":
    print("Running Dreamscape tab unit tests...")
    pytest.main(["-v", __file__]) 
