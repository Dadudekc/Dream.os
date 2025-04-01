import pytest
import sys
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

# Mock undetected_chromedriver before importing DreamscapeGenerationTab
sys.modules['undetected_chromedriver'] = MagicMock()

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from interfaces.pyqt.tabs.dreamscape_generation.DreamscapeGenerationTab import DreamscapeGenerationTab
from interfaces.pyqt.tabs.dreamscape_generation.services.ServiceInitializer import ServiceInitializer

# Initialize QApplication for tests
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

@pytest.fixture
def mock_services():
    template_manager = MagicMock()
    template_manager.get_available_templates.return_value = ['Template1', 'Template2']
    
    episode_generator = MagicMock()
    episode_generator.get_episodes.return_value = []
    
    return {
        'core_services': {
            'cycle_service': MagicMock(),
            'prompt_handler': MagicMock(),
            'discord_processor': MagicMock(),
            'task_orchestrator': MagicMock(),
            'dreamscape_service': MagicMock(),
        },
        'component_managers': {
            'template_manager': template_manager,
            'episode_generator': episode_generator,
            'context_manager': MagicMock(),
            'ui_manager': MagicMock(),
        },
        'output_dir': str(Path.cwd() / 'test_output')
    }

@pytest.fixture
def tab(qapp, mock_services):
    return DreamscapeGenerationTab(services=mock_services)

def test_init(tab, mock_services):
    """Test initialization of DreamscapeGenerationTab."""
    assert tab is not None
    assert tab.services == mock_services
    assert hasattr(tab, 'generation_controls')
    assert hasattr(tab, 'episode_list')
    assert hasattr(tab, 'context_tree')

def test_template_loading(tab, mock_services):
    """Test template loading functionality."""
    mock_templates = ['Template1', 'Template2']
    tab.template_manager.get_available_templates.return_value = mock_templates
    tab._load_initial_data()
    
    assert tab.generation_controls.template_dropdown.count() == 2
    assert [tab.generation_controls.template_dropdown.itemText(i) for i in range(2)] == mock_templates

@pytest.mark.asyncio
async def test_generate_episode_success(tab, mock_services):
    """Test successful episode generation."""
    # Setup mock episode
    mock_episode = {
        'content': "Test episode content",
        'title': "Test Episode",
        'id': "test-id",
        'context': {'key': 'value'}
    }
    
    # Setup async mock
    async def mock_generate(*args, **kwargs):
        return mock_episode
    tab.episode_generator.generate_episode.side_effect = mock_generate
    
    # Set UI state
    tab.generation_controls.target_chat_input.setText("test-chat")
    tab.generation_controls.model_dropdown.setCurrentText("GPT-4o")
    
    # Trigger generation
    await tab._on_generate_clicked({
        'template_name': "Template1",
        'target_chat': "test-chat",
        'model': "gpt-4o",
        'process_all': False,
        'reverse_order': False,
        'headless': False,
        'post_discord': False
    })
    
    # Verify episode generation was called with correct parameters
    tab.episode_generator.generate_episode.assert_called_once()
    
    # Verify UI updates
    assert tab.episode_list.episode_content.toPlainText() == "Test episode content"

@pytest.mark.asyncio
async def test_generate_episode_failure(tab, mock_services):
    """Test episode generation failure handling."""
    tab.episode_generator.generate_episode.side_effect = Exception("Generation failed")
    
    # Trigger generation
    await tab._on_generate_clicked({
        'template_name': "Template1",
        'target_chat': "test-chat",
        'model': "gpt-4o",
        'process_all': False,
        'reverse_order': False,
        'headless': False,
        'post_discord': False
    })

def test_cancel_generation(tab, mock_services):
    """Test cancellation of episode generation."""
    tab._on_cancel_clicked()
    tab.task_orchestrator.cancel_current_task.assert_called_once()

def test_episode_selection(tab, mock_services):
    """Test episode selection handling."""
    # Setup mock episode data
    mock_episode = {
        'content': "Selected episode content",
        'title': "Test Episode",
        'id': "test-id",
        'context': {'key': 'value'}
    }
    
    # Add and select episode
    tab.episode_list.add_episode(mock_episode)
    tab.episode_list.episode_list.setCurrentRow(0)
    
    # Verify content and context updates
    assert tab.episode_list.episode_content.toPlainText() == "Selected episode content"
    
    # Verify context tree update was triggered
    assert tab.context_tree.tree.topLevelItemCount() > 0

def test_context_tree_filtering(tab):
    """Test context tree filtering functionality."""
    # Setup mock context data
    context_data = {
        "test_key": "test_value",
        "other_key": "other_value"
    }
    
    # Update context tree
    tab.context_tree.update_context(context_data)
    
    # Test filtering
    tab.context_tree.filter_input.setText("test")
    
    # Verify filtering results
    root = tab.context_tree.tree.invisibleRootItem()
    visible_items = []
    for i in range(root.childCount()):
        item = root.child(i)
        if not item.isHidden():
            visible_items.append(item.text(0))
    
    assert "test_key" in visible_items
    assert "other_key" not in visible_items

@pytest.mark.asyncio
async def test_save_episode(tab, tmp_path):
    """Test episode saving functionality."""
    test_content = "Test episode content"
    tab.episode_list.episode_content.setPlainText(test_content)
    
    # Mock QFileDialog.getSaveFileName
    with patch('PyQt5.QtWidgets.QFileDialog.getSaveFileName', 
              return_value=(str(tmp_path / "test_episode.txt"), "Text files (*.txt)")):
        await tab.episode_list._save_episode("txt")
    
    # Verify file was saved correctly
    saved_file = tmp_path / "test_episode.txt"
    assert saved_file.exists()
    assert saved_file.read_text() == test_content

def test_service_initialization_without_services(qtbot):
    """Test that services are initialized correctly when none are provided."""
    # Create a mock ServiceInitializer instance
    mock_initializer = MagicMock(spec=ServiceInitializer)
    mock_services = {
        'core_services': {
            'cycle_service': None,
            'prompt_handler': None,
            'discord_processor': None,
            'task_orchestrator': None,
            'dreamscape_service': None,
        },
        'component_managers': {
            'template_manager': None,
            'episode_generator': None,
            'context_manager': None,
            'ui_manager': None,
        },
        'output_dir': 'test_output'
    }
    mock_initializer.initialize_services.return_value = mock_services

    # Patch the ServiceInitializer class to return our mock
    with patch('interfaces.pyqt.tabs.dreamscape_generation.DreamscapeGenerationTab.ServiceInitializer', return_value=mock_initializer):
        tab = DreamscapeGenerationTab()
        
        # Verify the ServiceInitializer was created and used
        assert hasattr(tab, 'service_initializer')
        assert tab.service_initializer == mock_initializer
        mock_initializer.initialize_services.assert_called_once()
        
        # Verify the services were stored correctly
        assert tab.services == mock_services

# Add more test cases as needed 
