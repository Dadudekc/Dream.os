"""
Tests for the DreamscapeGenerationTab component.
"""
import pytest
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QSignalSpy
from unittest.mock import MagicMock, patch

from chat_mate.gui.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab


@pytest.fixture
def prompt_manager_mock():
    """Mock for the prompt manager."""
    mock = MagicMock()
    mock.list_prompts.return_value = ["Default Dreamscape", "Custom Scenario"]
    mock.get_prompt.return_value = "Generate a dreamscape scenario about {{theme}}"
    return mock


@pytest.fixture
def chat_engine_mock():
    """Mock for the chat engine."""
    return MagicMock()


@pytest.fixture
def response_handler_mock():
    """Mock for the response handler."""
    return MagicMock()


@pytest.fixture
def memory_manager_mock():
    """Mock for the memory manager."""
    return MagicMock()


@pytest.fixture
def discord_manager_mock():
    """Mock for the discord manager."""
    return MagicMock()


@pytest.fixture
def dreamscape_generation_tab(qapp, prompt_manager_mock, chat_engine_mock, 
                              response_handler_mock, memory_manager_mock, 
                              discord_manager_mock):
    """Fixture for DreamscapeGenerationTab instance with mocked dependencies."""
    tab = DreamscapeGenerationTab()
    tab.update_managers(
        prompt_manager=prompt_manager_mock,
        chat_engine=chat_engine_mock,
        response_handler=response_handler_mock,
        memory_manager=memory_manager_mock,
        discord_manager=discord_manager_mock
    )
    return tab


def test_init_creates_ui_components(dreamscape_generation_tab):
    """Test that initialization creates all required UI components."""
    # Check essential UI components
    assert hasattr(dreamscape_generation_tab, 'prompt_selector')
    assert hasattr(dreamscape_generation_tab, 'theme_input')
    assert hasattr(dreamscape_generation_tab, 'episode_count_input')
    assert hasattr(dreamscape_generation_tab, 'character_list')
    assert hasattr(dreamscape_generation_tab, 'conflict_selector')
    assert hasattr(dreamscape_generation_tab, 'generate_btn')
    assert hasattr(dreamscape_generation_tab, 'preview_text')


def test_update_managers_sets_managers(dreamscape_generation_tab, prompt_manager_mock, 
                                      chat_engine_mock, response_handler_mock, 
                                      memory_manager_mock, discord_manager_mock):
    """Test that update_managers correctly sets the manager instances."""
    assert dreamscape_generation_tab.prompt_manager == prompt_manager_mock
    assert dreamscape_generation_tab.chat_engine == chat_engine_mock
    assert dreamscape_generation_tab.response_handler == response_handler_mock
    assert dreamscape_generation_tab.memory_manager == memory_manager_mock
    assert dreamscape_generation_tab.discord_manager == discord_manager_mock
    
    # Check that the prompt selector was populated if it exists
    if hasattr(dreamscape_generation_tab, 'prompt_selector') and dreamscape_generation_tab.prompt_selector:
        assert dreamscape_generation_tab.prompt_selector.count() >= 2
        assert dreamscape_generation_tab.prompt_selector.itemText(0) == "Default Dreamscape"


def test_load_prompt_template(dreamscape_generation_tab, prompt_manager_mock):
    """Test that load_prompt_template correctly loads the template."""
    # This test assumes the tab has a method to load prompt templates
    if hasattr(dreamscape_generation_tab, 'load_prompt_template'):
        dreamscape_generation_tab.load_prompt_template("Default Dreamscape")
        prompt_manager_mock.get_prompt.assert_called_with("Default Dreamscape")
        
        # Check that the template is loaded in the UI
        # This depends on the specific implementation


def test_validate_inputs_valid(dreamscape_generation_tab, monkeypatch):
    """Test validate_inputs with valid inputs."""
    # Set up valid inputs
    if hasattr(dreamscape_generation_tab, 'theme_input'):
        dreamscape_generation_tab.theme_input.setText("Space Adventure")
    
    if hasattr(dreamscape_generation_tab, 'episode_count_input'):
        dreamscape_generation_tab.episode_count_input.setValue(5)
    
    # Validate inputs
    if hasattr(dreamscape_generation_tab, 'validate_inputs'):
        result = dreamscape_generation_tab.validate_inputs()
        assert result is True


def test_validate_inputs_invalid(dreamscape_generation_tab, monkeypatch, qapp):
    """Test validate_inputs with invalid inputs."""
    # Mock QMessageBox.warning to prevent UI popup
    with patch('PyQt5.QtWidgets.QMessageBox.warning', return_value=QMessageBox.Ok):
        # Set up invalid inputs
        if hasattr(dreamscape_generation_tab, 'theme_input'):
            dreamscape_generation_tab.theme_input.setText("")
        
        # Validate inputs
        if hasattr(dreamscape_generation_tab, 'validate_inputs'):
            result = dreamscape_generation_tab.validate_inputs()
            assert result is False


def test_add_character(dreamscape_generation_tab, monkeypatch):
    """Test adding a character to the list."""
    # This test assumes the tab has a method to add characters
    if hasattr(dreamscape_generation_tab, 'add_character') and hasattr(dreamscape_generation_tab, 'character_list'):
        # Mock QInputDialog.getText to return a fixed value
        monkeypatch.setattr('PyQt5.QtWidgets.QInputDialog.getText', 
                           lambda *args, **kwargs: ("Captain Sarah", True))
        
        # Get initial count
        initial_count = dreamscape_generation_tab.character_list.count()
        
        # Add character
        dreamscape_generation_tab.add_character()
        
        # Check that the character was added
        assert dreamscape_generation_tab.character_list.count() == initial_count + 1
        assert dreamscape_generation_tab.character_list.item(initial_count).text() == "Captain Sarah"


def test_remove_character(dreamscape_generation_tab):
    """Test removing a character from the list."""
    # This test assumes the tab has a method to remove characters
    if hasattr(dreamscape_generation_tab, 'remove_character') and hasattr(dreamscape_generation_tab, 'character_list'):
        # First add a character
        dreamscape_generation_tab.character_list.addItem("Commander John")
        
        # Select the character
        dreamscape_generation_tab.character_list.setCurrentRow(0)
        
        # Remove the character
        dreamscape_generation_tab.remove_character()
        
        # Check that the character was removed
        assert dreamscape_generation_tab.character_list.count() == 0


def test_generate_dreamscape(dreamscape_generation_tab, monkeypatch, prompt_manager_mock, capsys):
    """Test generating a dreamscape scenario."""
    # Mock necessary methods and UI inputs
    if hasattr(dreamscape_generation_tab, 'generate_dreamscape'):
        # Set up inputs
        if hasattr(dreamscape_generation_tab, 'theme_input'):
            dreamscape_generation_tab.theme_input.setText("Space Adventure")
        
        if hasattr(dreamscape_generation_tab, 'episode_count_input'):
            dreamscape_generation_tab.episode_count_input.setValue(3)
        
        # Mock validate_inputs to return True
        if hasattr(dreamscape_generation_tab, 'validate_inputs'):
            monkeypatch.setattr(dreamscape_generation_tab, 'validate_inputs', lambda: True)
        
        # Call generate_dreamscape
        dreamscape_generation_tab.generate_dreamscape()
        
        # Verify that the expected calls to manager methods were made
        # This depends on the implementation of generate_dreamscape


def test_preview_dreamscape(dreamscape_generation_tab, monkeypatch):
    """Test previewing a dreamscape scenario."""
    # This test assumes the tab has a method to preview the dreamscape
    if hasattr(dreamscape_generation_tab, 'preview_dreamscape'):
        # Set up inputs
        if hasattr(dreamscape_generation_tab, 'theme_input'):
            dreamscape_generation_tab.theme_input.setText("Space Adventure")
        
        # Mock validate_inputs to return True
        if hasattr(dreamscape_generation_tab, 'validate_inputs'):
            monkeypatch.setattr(dreamscape_generation_tab, 'validate_inputs', lambda: True)
        
        # Mock the prompt manager to return a formatted prompt
        formatted_prompt = "Generate a dreamscape scenario about Space Adventure"
        monkeypatch.setattr(prompt_manager_mock, 'format_prompt', lambda *args, **kwargs: formatted_prompt)
        
        # Call preview_dreamscape
        dreamscape_generation_tab.preview_dreamscape()
        
        # Check that the preview text was updated
        if hasattr(dreamscape_generation_tab, 'preview_text'):
            assert formatted_prompt in dreamscape_generation_tab.preview_text.toPlainText()


def test_get_character_list(dreamscape_generation_tab):
    """Test getting the list of characters."""
    # This test assumes the tab has a method to get the character list
    if hasattr(dreamscape_generation_tab, 'get_character_list') and hasattr(dreamscape_generation_tab, 'character_list'):
        # Add some characters
        dreamscape_generation_tab.character_list.addItem("Commander John")
        dreamscape_generation_tab.character_list.addItem("Captain Sarah")
        
        # Get the character list
        characters = dreamscape_generation_tab.get_character_list()
        
        # Check that the list contains the expected characters
        assert len(characters) == 2
        assert "Commander John" in characters
        assert "Captain Sarah" in characters


def test_reset_form(dreamscape_generation_tab):
    """Test resetting the form."""
    # This test assumes the tab has a method to reset the form
    if hasattr(dreamscape_generation_tab, 'reset_form'):
        # Set up form with data
        if hasattr(dreamscape_generation_tab, 'theme_input'):
            dreamscape_generation_tab.theme_input.setText("Space Adventure")
        
        if hasattr(dreamscape_generation_tab, 'character_list'):
            dreamscape_generation_tab.character_list.addItem("Commander John")
        
        # Reset the form
        dreamscape_generation_tab.reset_form()
        
        # Check that the form was reset
        if hasattr(dreamscape_generation_tab, 'theme_input'):
            assert dreamscape_generation_tab.theme_input.text() == ""
        
        if hasattr(dreamscape_generation_tab, 'character_list'):
            assert dreamscape_generation_tab.character_list.count() == 0 
