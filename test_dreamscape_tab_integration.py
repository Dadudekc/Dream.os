import pytest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

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

# Skip tests if components are not available
pytestmark = pytest.mark.skipif(
    not DREAMSCAPE_TAB_AVAILABLE,
    reason="Dreamscape tab components not available"
)

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

# Integration tests begin here

def test_full_episode_generation_workflow(dreamscape_tab, mock_services, mock_chat_data, tmp_path):
    """Test the complete episode generation workflow."""
    # Skip if required components are not available
    if not hasattr(dreamscape_tab, 'chat_combo') or not hasattr(dreamscape_tab, 'episode_list'):
        pytest.skip("Required components not available")
    
    # Setup mocks
    mock_services['chat_manager'].get_all_chat_titles.return_value = mock_chat_data
    mock_services['chat_manager'].get_chat_by_title.return_value = mock_chat_data[0]
    
    # Mock episode generation - we'll simulate writing a file
    def generate_episode_side_effect(chat_data, output_path, *args, **kwargs):
        output_file = Path(output_path) / f"episode_{chat_data['title'].replace(' ', '_')}.md"
        output_file.write_text(f"# Generated from {chat_data['title']}\n\nTest episode content")
        return str(output_file)
    
    mock_services['episode_generator'].generate_episode.side_effect = generate_episode_side_effect
    
    # Patch the tab's services
    dreamscape_tab.chat_manager = mock_services['chat_manager']
    dreamscape_tab.episode_generator = mock_services['episode_generator']
    dreamscape_tab.output_dir = tmp_path / "dreamscape"
    
    # 1. Load the chats
    dreamscape_tab.load_available_chats()
    assert dreamscape_tab.chat_combo.count() == 2
    
    # 2. Select a chat
    dreamscape_tab.chat_combo.setCurrentIndex(0)
    
    # 3. Generate an episode
    dreamscape_tab.generate_episode_from_selected_chat()
    
    # Verify call to episode generator
    mock_services['episode_generator'].generate_episode.assert_called_once()
    
    # 4. Verify episode list is refreshed and contains the new episode
    # This would be triggered by signal in real app, we'll call directly
    dreamscape_tab.load_episode_list()
    
    # Check that our episode file exists
    assert Path(dreamscape_tab.output_dir / "episode_Test_Chat_1.md").exists()
    
    # Ensure the list has the item
    found_episode = False
    for i in range(dreamscape_tab.episode_list.count()):
        if "Test_Chat_1" in dreamscape_tab.episode_list.item(i).text():
            found_episode = True
            break
    
    assert found_episode, "The generated episode should appear in the list"

def test_service_interaction(dreamscape_tab, mock_services):
    """Test interactions between the tab and its services."""
    # Skip if required components are not available
    if not hasattr(dreamscape_tab, 'chat_combo'):
        pytest.skip("Required components not available")
    
    # Patch the tab's services
    dreamscape_tab.chat_manager = mock_services['chat_manager']
    dreamscape_tab.context_synthesizer = mock_services['context_synthesizer']
    dreamscape_tab.episode_generator = mock_services['episode_generator']
    
    # Setup mocks
    mock_services['chat_manager'].get_all_chat_titles.return_value = []
    mock_services['chat_manager'].get_chat_by_title.return_value = {'title': 'Test Chat', 'messages': []}
    mock_services['context_synthesizer'].synthesize_context.return_value = "Synthesized context"
    
    # Load chats - should call chat_manager.get_all_chat_titles
    dreamscape_tab.load_available_chats()
    mock_services['chat_manager'].get_all_chat_titles.assert_called_once()
    
    # Set a chat title and generate an episode
    # This should trigger a chain of service calls
    dreamscape_tab.chat_combo.addItem("Test Chat")
    dreamscape_tab.chat_combo.setCurrentIndex(0)
    
    # Call generate
    dreamscape_tab.generate_episode_from_selected_chat()
    
    # Verify service interactions
    mock_services['chat_manager'].get_chat_by_title.assert_called_once_with("Test Chat")
    mock_services['context_synthesizer'].synthesize_context.assert_called_once()
    mock_services['episode_generator'].generate_episode.assert_called_once()

def test_ui_state_during_generation(dreamscape_tab, mock_services):
    """Test UI state changes during episode generation."""
    # Skip if required components are not available
    if not hasattr(dreamscape_tab, 'chat_combo') or not hasattr(dreamscape_tab, 'generate_button'):
        pytest.skip("Required components not available")
    
    # Patch the tab's services
    dreamscape_tab.chat_manager = mock_services['chat_manager']
    dreamscape_tab.context_synthesizer = mock_services['context_synthesizer']
    dreamscape_tab.episode_generator = mock_services['episode_generator']
    
    # Setup mocks
    mock_services['chat_manager'].get_chat_by_title.return_value = {'title': 'Test Chat', 'messages': []}
    mock_services['episode_generator'].generate_episode.return_value = "episode.md"
    
    # Set a chat
    dreamscape_tab.chat_combo.addItem("Test Chat")
    dreamscape_tab.chat_combo.setCurrentIndex(0)
    
    # Capture the initial state
    initial_button_enabled = dreamscape_tab.generate_button.isEnabled()
    
    # Start generation - this would normally disable UI elements during processing
    dreamscape_tab.set_ui_generating_state(True)
    
    # Verify UI is in generating state
    assert not dreamscape_tab.generate_button.isEnabled(), "Generate button should be disabled during generation"
    
    # End generation
    dreamscape_tab.set_ui_generating_state(False)
    
    # Verify UI returned to normal state
    assert dreamscape_tab.generate_button.isEnabled() == initial_button_enabled, "Generate button should return to initial state"

def test_error_handling(dreamscape_tab, mock_services):
    """Test error handling during episode generation."""
    # Skip if required components are not available
    if not hasattr(dreamscape_tab, 'chat_combo') or not hasattr(dreamscape_tab, 'status_label'):
        pytest.skip("Required components not available")
    
    # Patch the tab's services
    dreamscape_tab.chat_manager = mock_services['chat_manager']
    dreamscape_tab.context_synthesizer = mock_services['context_synthesizer']
    dreamscape_tab.episode_generator = mock_services['episode_generator']
    
    # Setup the chat manager to raise an exception
    mock_services['chat_manager'].get_chat_by_title.side_effect = Exception("Test error")
    
    # Set a chat
    dreamscape_tab.chat_combo.addItem("Test Chat")
    dreamscape_tab.chat_combo.setCurrentIndex(0)
    
    # Try to generate - this should catch the exception
    dreamscape_tab.generate_episode_from_selected_chat()
    
    # Verify error handling
    assert "Error" in dreamscape_tab.status_label.text()
    mock_services['logger'].error.assert_called()

def test_share_to_discord_flow(dreamscape_tab, mock_services, tmp_path):
    """Test the flow for sharing an episode to Discord."""
    # Skip if required components are not available
    if not hasattr(dreamscape_tab, 'episode_list') or not hasattr(dreamscape_tab, 'share_button'):
        pytest.skip("Required components not available")
    
    # Create a test episode file
    output_dir = tmp_path / "dreamscape"
    test_episode = output_dir / "test_episode.md"
    test_episode.write_text("# Test Episode\n\nThis is a test episode.")
    
    # Patch the tab's services
    dreamscape_tab.dreamscape_service = mock_services['dreamscape_service']
    dreamscape_tab.output_dir = output_dir
    
    # Load the episode list
    dreamscape_tab.load_episode_list()
    
    # Select an episode - assuming it's the first one
    from PyQt5.QtWidgets import QListWidgetItem
    item = QListWidgetItem("test_episode.md")
    item.setData(Qt.UserRole, str(test_episode))
    dreamscape_tab.episode_list.addItem(item)
    dreamscape_tab.episode_list.setCurrentRow(0)
    
    # Trigger share to Discord
    dreamscape_tab.share_selected_episode_to_discord()
    
    # Verify service interaction
    mock_services['dreamscape_service'].share_to_discord.assert_called_once()
    # The first argument should be the file path
    assert mock_services['dreamscape_service'].share_to_discord.call_args[0][0] == str(test_episode)

if __name__ == "__main__":
    print("Running Dreamscape tab integration tests...")
    pytest.main(["-v", __file__]) 
