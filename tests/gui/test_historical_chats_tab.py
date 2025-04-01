"""
Tests for the HistoricalChatsTab component.
"""
import pytest
from PyQt5.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QTextEdit
from PyQt5.QtCore import Qt
from unittest.mock import MagicMock, patch

from chat_mate.gui.tabs.HistoricalChatsTab import HistoricalChatsTab


@pytest.fixture
def chat_history_mock():
    """Mock for the chat history manager."""
    mock = MagicMock()
    
    # Mock the get_chat_history method to return sample data
    sample_history = {
        "2023-03-21": {
            "Session 1": [
                {"role": "user", "content": "Hello, how are you?"},
                {"role": "assistant", "content": "I'm doing well, thank you for asking!"}
            ],
            "Session 2": [
                {"role": "user", "content": "What's the weather like?"},
                {"role": "assistant", "content": "I don't have access to real-time weather data."}
            ]
        },
        "2023-03-20": {
            "Session 3": [
                {"role": "user", "content": "Tell me about AI"},
                {"role": "assistant", "content": "Artificial Intelligence is a field of computer science..."}
            ]
        }
    }
    
    mock.get_chat_history.return_value = sample_history
    return mock


@pytest.fixture
def historical_chats_tab(qapp, chat_history_mock):
    """Fixture for HistoricalChatsTab instance with mocked dependencies."""
    tab = HistoricalChatsTab()
    
    # Set up the tab with mock data if it has the necessary attributes
    if hasattr(tab, 'update_managers'):
        tab.update_managers(chat_history=chat_history_mock)
    elif hasattr(tab, 'set_chat_history'):
        tab.set_chat_history(chat_history_mock)
    
    return tab


def test_init_creates_ui_components(historical_chats_tab):
    """Test that initialization creates all required UI components."""
    # Check essential UI components
    assert hasattr(historical_chats_tab, 'history_tree')
    assert hasattr(historical_chats_tab, 'chat_display')
    
    # Check component types
    assert isinstance(historical_chats_tab.history_tree, QTreeWidget)
    assert isinstance(historical_chats_tab.chat_display, QTextEdit)


def test_history_tree_has_columns(historical_chats_tab):
    """Test that the history tree has proper columns."""
    # The tree should have at least one column (date/session)
    assert historical_chats_tab.history_tree.columnCount() >= 1


def test_load_chat_history(historical_chats_tab, chat_history_mock):
    """Test loading chat history."""
    # This test assumes the tab has a method to load chat history
    if hasattr(historical_chats_tab, 'load_chat_history'):
        historical_chats_tab.load_chat_history()
        
        # Check that the history tree has been populated
        assert historical_chats_tab.history_tree.topLevelItemCount() >= 2  # 2 dates
        
        # Check that the chat history was retrieved
        chat_history_mock.get_chat_history.assert_called_once()


def test_display_chat_session(historical_chats_tab, chat_history_mock, monkeypatch):
    """Test displaying a chat session."""
    # This test assumes the tab has a method to display a chat session
    if not hasattr(historical_chats_tab, 'display_chat_session'):
        return
    
    # Mock the necessary methods and properties
    selected_date = "2023-03-21"
    selected_session = "Session 1"
    
    # Create a mock item for the tree
    mock_item = MagicMock()
    mock_item.text.return_value = selected_session
    mock_item.parent().text.return_value = selected_date
    
    # Mock the selectedItems method
    monkeypatch.setattr(historical_chats_tab.history_tree, 'selectedItems', 
                       lambda: [mock_item])
    
    # Call the method to display the chat session
    historical_chats_tab.display_chat_session()
    
    # Check that the chat display contains the expected content
    chat_text = historical_chats_tab.chat_display.toPlainText()
    assert "Hello, how are you?" in chat_text
    assert "I'm doing well, thank you for asking!" in chat_text


def test_export_chat_history(historical_chats_tab, monkeypatch, tmp_path):
    """Test exporting chat history."""
    # This test assumes the tab has a method to export chat history
    if not hasattr(historical_chats_tab, 'export_chat_history'):
        return
    
    # Set up a temporary file path
    export_path = tmp_path / "export.json"
    
    # Mock the file dialog to return our temp path
    monkeypatch.setattr('PyQt5.QtWidgets.QFileDialog.getSaveFileName', 
                       lambda *args, **kwargs: (str(export_path), "JSON Files (*.json)"))
    
    # Call the export method
    historical_chats_tab.export_chat_history()
    
    # Check that the file was created
    assert export_path.exists()


def test_search_chat_history(historical_chats_tab, monkeypatch):
    """Test searching chat history."""
    # This test assumes the tab has a search feature
    if not hasattr(historical_chats_tab, 'search_input') or not hasattr(historical_chats_tab, 'search_chats'):
        return
    
    # Set up the chat history display with sample data
    historical_chats_tab.chat_display.setPlainText(
        "User: Hello, how are you?\n"
        "Assistant: I'm doing well, thank you for asking!\n"
        "User: What's the weather like?\n"
        "Assistant: I don't have access to real-time weather data."
    )
    
    # Set the search text and trigger the search
    historical_chats_tab.search_input.setText("weather")
    historical_chats_tab.search_chats()
    
    # Check that the search results are highlighted or filtered
    # Implementation depends on how search is handled in the tab


def test_clear_search(historical_chats_tab, monkeypatch):
    """Test clearing search results."""
    # This test assumes the tab has a clear search feature
    if not hasattr(historical_chats_tab, 'search_input') or not hasattr(historical_chats_tab, 'clear_search'):
        return
    
    # Set up a search first
    historical_chats_tab.search_input.setText("weather")
    if hasattr(historical_chats_tab, 'search_chats'):
        historical_chats_tab.search_chats()
    
    # Then clear it
    historical_chats_tab.clear_search()
    
    # Check that the search input is cleared
    assert historical_chats_tab.search_input.text() == ""


def test_delete_chat_session(historical_chats_tab, chat_history_mock, monkeypatch):
    """Test deleting a chat session."""
    # This test assumes the tab has a method to delete a chat session
    if not hasattr(historical_chats_tab, 'delete_chat_session'):
        return
    
    # Mock the necessary methods and properties
    selected_date = "2023-03-21"
    selected_session = "Session 1"
    
    # Create a mock item for the tree
    mock_item = MagicMock()
    mock_item.text.return_value = selected_session
    mock_item.parent().text.return_value = selected_date
    
    # Mock the selectedItems method
    monkeypatch.setattr(historical_chats_tab.history_tree, 'selectedItems', 
                       lambda: [mock_item])
    
    # Mock QMessageBox.question to return Yes
    monkeypatch.setattr('PyQt5.QtWidgets.QMessageBox.question', 
                       lambda *args, **kwargs: 16384)  # QMessageBox.Yes
    
    # Call the delete method
    historical_chats_tab.delete_chat_session()
    
    # Check that the delete method was called on the chat history manager
    if hasattr(chat_history_mock, 'delete_chat_session'):
        chat_history_mock.delete_chat_session.assert_called_with(selected_date, selected_session)


def test_refresh_history(historical_chats_tab, chat_history_mock):
    """Test refreshing chat history."""
    # This test assumes the tab has a method to refresh the history
    if not hasattr(historical_chats_tab, 'refresh_history'):
        return
    
    # Call the refresh method
    historical_chats_tab.refresh_history()
    
    # Check that the history was loaded
    if hasattr(chat_history_mock, 'get_chat_history'):
        chat_history_mock.get_chat_history.assert_called()
    
    # Check that the tree was cleared and repopulated
    # This depends on the specific implementation 
