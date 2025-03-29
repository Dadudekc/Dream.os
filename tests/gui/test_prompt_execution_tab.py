"""
Tests for the PromptExecutionTab component.
"""
import pytest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from unittest.mock import MagicMock, patch

from chat_mate.gui.tabs.PromptExecutionTab import PromptExecutionTab


@pytest.fixture
def prompt_manager_mock():
    """Mock for the prompt manager."""
    mock = MagicMock()
    mock.list_prompts.return_value = ["Test Prompt 1", "Test Prompt 2"]
    mock.get_prompt.return_value = "This is a test prompt"
    return mock


@pytest.fixture
def chat_manager_mock():
    """Mock for the chat manager."""
    return MagicMock()


@pytest.fixture
def response_handler_mock():
    """Mock for the response handler."""
    return MagicMock()


@pytest.fixture
def prompt_execution_tab(qapp, prompt_manager_mock, chat_manager_mock, response_handler_mock):
    """Fixture for PromptExecutionTab instance with mocked dependencies."""
    tab = PromptExecutionTab()
    tab.update_managers(
        prompt_manager=prompt_manager_mock,
        chat_manager=chat_manager_mock,
        response_handler=response_handler_mock
    )
    return tab


def test_init_creates_ui_components(prompt_execution_tab):
    """Test that initialization creates all required UI components."""
    # Check essential UI components
    assert hasattr(prompt_execution_tab, 'prompt_selector')
    assert hasattr(prompt_execution_tab, 'prompt_editor')
    assert hasattr(prompt_execution_tab, 'prompt_type_selector')
    assert hasattr(prompt_execution_tab, 'execution_mode_combo')
    assert hasattr(prompt_execution_tab, 'exclusion_list')
    assert hasattr(prompt_execution_tab, 'execute_prompt_btn')


def test_update_managers_sets_managers(prompt_execution_tab, prompt_manager_mock, chat_manager_mock, response_handler_mock):
    """Test that update_managers correctly sets the manager instances."""
    assert prompt_execution_tab.prompt_manager == prompt_manager_mock
    assert prompt_execution_tab.chat_manager == chat_manager_mock
    assert prompt_execution_tab.response_handler == response_handler_mock
    
    # Check that the prompt selector was populated
    assert prompt_execution_tab.prompt_selector.count() == 2
    assert prompt_execution_tab.prompt_selector.itemText(0) == "Test Prompt 1"
    assert prompt_execution_tab.prompt_selector.itemText(1) == "Test Prompt 2"


def test_load_prompt_sets_text(prompt_execution_tab, prompt_manager_mock):
    """Test that load_prompt correctly sets the prompt text."""
    prompt_execution_tab.load_prompt("Test Prompt 1")
    prompt_manager_mock.get_prompt.assert_called_once_with("Test Prompt 1")
    assert prompt_execution_tab.prompt_editor.toPlainText() == "This is a test prompt"


def test_load_prompt_handles_missing_manager(prompt_execution_tab):
    """Test that load_prompt handles missing prompt manager gracefully."""
    prompt_execution_tab.prompt_manager = None
    # Should not raise an exception
    prompt_execution_tab.load_prompt("Test Prompt")
    assert prompt_execution_tab.prompt_editor.toPlainText() == ""


def test_update_execution_mode_updates_ui(prompt_execution_tab):
    """Test that update_execution_mode correctly updates the UI."""
    # Test direct execution mode
    prompt_execution_tab.update_execution_mode("Direct Execution")
    assert prompt_execution_tab.prompt_stack.currentIndex() == 0
    assert prompt_execution_tab.execute_prompt_btn.text() == "Execute Prompt"
    
    # Test prompt cycle mode
    prompt_execution_tab.update_execution_mode("Prompt Cycle Mode")
    assert prompt_execution_tab.prompt_stack.currentIndex() == 1
    assert prompt_execution_tab.execute_prompt_btn.text() == "Start Prompt Cycle"


def test_load_prompt_data(prompt_execution_tab):
    """Test that load_prompt_data correctly handles prompt data."""
    test_data = {
        "text": "Test prompt data",
        "type": "Custom",
        "is_cycle": False
    }
    prompt_execution_tab.load_prompt_data(test_data)
    
    assert prompt_execution_tab.prompt_editor.toPlainText() == "Test prompt data"
    assert prompt_execution_tab.prompt_type_selector.currentText() == "Custom"
    assert prompt_execution_tab.execution_mode_combo.currentText() == "Direct Execution"
    
    # Test cycle mode
    cycle_data = {
        "text": "Test cycle prompt",
        "type": "Community",
        "is_cycle": True,
        "cycle_items": ["Item 1", "Item 2", "Item 3"]
    }
    prompt_execution_tab.load_prompt_data(cycle_data)
    
    assert prompt_execution_tab.prompt_editor.toPlainText() == "Test cycle prompt"
    assert prompt_execution_tab.prompt_type_selector.currentText() == "Community"
    assert prompt_execution_tab.execution_mode_combo.currentText() == "Prompt Cycle Mode"
    assert prompt_execution_tab.prompt_cycle_list.count() == 3
    assert prompt_execution_tab.prompt_cycle_list.item(0).text() == "Item 1"


def test_exclusion_list_management(prompt_execution_tab, monkeypatch):
    """Test that exclusion list management works correctly."""
    # Mock QInputDialog.getText to return a fixed value
    monkeypatch.setattr('PyQt5.QtWidgets.QInputDialog.getText', lambda *args, **kwargs: ("Test Exclusion", True))
    
    # Add exclusion
    prompt_execution_tab.add_exclusion()
    assert prompt_execution_tab.exclusion_list.count() == 1
    assert prompt_execution_tab.exclusion_list.item(0).text() == "Test Exclusion"
    
    # Test getting excluded chats
    excluded_chats = prompt_execution_tab.get_excluded_chats()
    assert len(excluded_chats) == 1
    assert excluded_chats[0] == "Test Exclusion"
    
    # Test removing exclusion
    prompt_execution_tab.exclusion_list.setCurrentRow(0)
    prompt_execution_tab.remove_exclusion()
    assert prompt_execution_tab.exclusion_list.count() == 0


def test_execute_prompt_direct_mode(prompt_execution_tab, capsys):
    """Test execute_prompt in direct execution mode."""
    prompt_execution_tab.prompt_editor.setPlainText("Test execution")
    prompt_execution_tab.execution_mode_combo.setCurrentText("Direct Execution")
    
    prompt_execution_tab.execute_prompt()
    captured = capsys.readouterr()
    assert "Executing Prompt:" in captured.out
    assert "Test execution" in captured.out


def test_execute_prompt_cycle_mode(prompt_execution_tab, capsys):
    """Test execute_prompt in prompt cycle mode."""
    prompt_execution_tab.execution_mode_combo.setCurrentText("Prompt Cycle Mode")
    
    prompt_execution_tab.execute_prompt()
    captured = capsys.readouterr()
    assert "Starting prompt cycle..." in captured.out


def test_save_prompt_with_valid_manager(prompt_execution_tab, prompt_manager_mock, capsys):
    """Test save_prompt with a valid prompt manager."""
    prompt_execution_tab.save_prompt()
    captured = capsys.readouterr()
    assert "Saving prompt..." in captured.out


def test_save_prompt_with_missing_manager(prompt_execution_tab, capsys):
    """Test save_prompt handles missing prompt manager gracefully."""
    prompt_execution_tab.prompt_manager = None
    prompt_execution_tab.save_prompt()
    captured = capsys.readouterr()
    assert "Error: Prompt manager not available" in captured.out


def test_reset_prompts_with_valid_manager(prompt_execution_tab, prompt_manager_mock, capsys):
    """Test reset_prompts with a valid prompt manager."""
    prompt_execution_tab.reset_prompts()
    captured = capsys.readouterr()
    assert "Resetting prompts..." in captured.out


def test_reset_prompts_with_missing_manager(prompt_execution_tab, capsys):
    """Test reset_prompts handles missing prompt manager gracefully."""
    prompt_execution_tab.prompt_manager = None
    prompt_execution_tab.reset_prompts()
    captured = capsys.readouterr()
    assert "Error: Prompt manager not available" in captured.out 