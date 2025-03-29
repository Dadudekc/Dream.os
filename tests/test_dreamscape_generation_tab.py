import pytest
import os
import json
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from interfaces.pyqt.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab

# Create QApplication instance for tests
@pytest.fixture(scope="session")
def qapp():
    app = QApplication([])
    yield app
    app.quit()

# Mock services
@pytest.fixture
def mock_services():
    return {
        'dispatcher': MagicMock(),
        'prompt_manager': MagicMock(),
        'chat_manager': MagicMock(),
        'response_handler': MagicMock(),
        'memory_manager': MagicMock(),
        'discord_manager': MagicMock(),
        'ui_logic': MagicMock(),
        'config_manager': MagicMock(),
        'logger': MagicMock()
    }

@pytest.fixture
def dreamscape_tab(qapp, mock_services, tmp_path):
    # Create a temporary output directory
    output_dir = tmp_path / "dreamscape_output"
    output_dir.mkdir()
    mock_services['config_manager'].get.return_value = str(output_dir)
    
    tab = DreamscapeGenerationTab(**mock_services)
    return tab

def test_init(dreamscape_tab):
    """Test initialization of DreamscapeGenerationTab"""
    assert dreamscape_tab is not None
    assert dreamscape_tab.episode_list is not None
    assert dreamscape_tab.episode_content is not None
    assert dreamscape_tab.output_display is not None

def test_refresh_episode_list(dreamscape_tab, tmp_path):
    """Test episode list refresh functionality"""
    # Create a test episode file
    output_dir = tmp_path / "dreamscape_output"
    test_episode = output_dir / "20240325_test_episode.txt"
    test_episode.write_text("Test episode content")
    
    # Refresh episode list
    dreamscape_tab.refresh_episode_list()
    
    # Check if episode appears in list
    assert dreamscape_tab.episode_list.count() == 1
    item_text = dreamscape_tab.episode_list.item(0).text()
    assert "test episode" in item_text.lower()

@pytest.mark.asyncio
async def test_generate_dreamscape_episodes(dreamscape_tab, mock_services):
    """Test episode generation process"""
    # Mock the dreamscape generator
    mock_generator = MagicMock()
    mock_generator.get_episode_number.return_value = 1
    mock_generator.generate_dreamscape_episodes.return_value = ["Episode 1"]
    dreamscape_tab.dreamscape_generator = mock_generator
    
    # Enable Discord posting
    dreamscape_tab.post_discord_checkbox.setChecked(True)
    
    # Trigger generation
    await dreamscape_tab.generate_dreamscape_episodes()
    
    # Verify generator was called
    mock_generator.generate_dreamscape_episodes.assert_called_once()
    
    # Verify UI updates
    assert dreamscape_tab.generate_episodes_btn.isEnabled()

def test_share_to_discord(dreamscape_tab, mock_services):
    """Test Discord sharing functionality"""
    # Set up test content
    test_content = "Test episode content"
    dreamscape_tab.episode_content.setPlainText(test_content)
    
    # Trigger sharing
    dreamscape_tab.share_to_discord()
    
    # Verify Discord manager was called
    mock_services['discord_manager'].send_message.assert_called_once_with(test_content)

def test_context_memory_refresh(dreamscape_tab):
    """Test context memory refresh functionality"""
    # Mock context data
    mock_context = {
        "episode_count": 5,
        "last_updated": "2024-03-25",
        "active_themes": ["Adventure", "Mystery"],
        "recent_episodes": [
            {
                "title": "Test Episode",
                "timestamp": "2024-03-25",
                "themes": ["Adventure"]
            }
        ]
    }
    
    # Mock the generator's get_context_summary method
    dreamscape_tab.dreamscape_generator = MagicMock()
    dreamscape_tab.dreamscape_generator.get_context_summary.return_value = mock_context
    
    # Refresh context memory
    dreamscape_tab.refresh_context_memory()
    
    # Verify tree widget was populated
    assert dreamscape_tab.context_tree.topLevelItemCount() > 0

def test_load_schedule_settings(dreamscape_tab, tmp_path):
    """Test loading schedule settings"""
    # Create test schedule file
    output_dir = tmp_path / "dreamscape_output"
    schedule_file = output_dir / "context_update_schedule.json"
    schedule_data = {
        "enabled": True,
        "interval_days": 7,
        "target_chat": "Dreamscape Chat",
        "next_update": "2024-03-32T12:00:00Z"
    }
    schedule_file.write_text(json.dumps(schedule_data))
    
    # Load settings
    dreamscape_tab.load_schedule_settings()
    
    # Verify settings were applied
    assert dreamscape_tab.auto_update_checkbox.isChecked()
    assert "7" in dreamscape_tab.update_interval_combo.currentText()

def test_validate_schedule_settings(dreamscape_tab):
    """Test schedule settings validation"""
    # Test with checkbox unchecked
    dreamscape_tab.auto_update_checkbox.setChecked(False)
    assert not dreamscape_tab._validate_schedule_settings()
    
    # Test with checkbox checked
    dreamscape_tab.auto_update_checkbox.setChecked(True)
    assert dreamscape_tab._validate_schedule_settings()

# Add more test cases as needed 