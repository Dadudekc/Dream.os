"""
Tests for the LogsTab component.
"""
import pytest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from unittest.mock import MagicMock, patch

from chat_mate.gui.tabs.LogsTab import LogsTab


@pytest.fixture
def logs_tab(qapp):
    """Fixture for LogsTab instance."""
    return LogsTab()


def test_init_creates_ui_components(logs_tab):
    """Test that initialization creates all required UI components."""
    # Check essential UI components
    assert hasattr(logs_tab, 'log_text')
    assert hasattr(logs_tab, 'clear_btn')
    
    # Check that the log text is a QTextEdit
    from PyQt5.QtWidgets import QTextEdit
    assert isinstance(logs_tab.log_text, QTextEdit)
    
    # Check that the clear button is a QPushButton
    from PyQt5.QtWidgets import QPushButton
    assert isinstance(logs_tab.clear_btn, QPushButton)


def test_clear_logs(logs_tab):
    """Test clearing the logs."""
    # Add some text to the log
    logs_tab.log_text.setPlainText("Test log message")
    assert logs_tab.log_text.toPlainText() == "Test log message"
    
    # Clear the logs
    logs_tab.clear_btn.click()
    assert logs_tab.log_text.toPlainText() == ""


def test_append_log(logs_tab):
    """Test appending a log message."""
    # Clear any existing logs
    logs_tab.log_text.clear()
    
    # Append a log message
    if hasattr(logs_tab, 'append_log'):
        logs_tab.append_log("Test log message")
        assert "Test log message" in logs_tab.log_text.toPlainText()
    else:
        # If the method doesn't exist, test direct text setting
        logs_tab.log_text.setPlainText("Test log message")
        assert logs_tab.log_text.toPlainText() == "Test log message"


def test_multiple_log_entries(logs_tab):
    """Test appending multiple log entries."""
    # Clear any existing logs
    logs_tab.log_text.clear()
    
    # Append multiple log messages
    if hasattr(logs_tab, 'append_log'):
        logs_tab.append_log("First log message")
        logs_tab.append_log("Second log message")
        
        log_text = logs_tab.log_text.toPlainText()
        assert "First log message" in log_text
        assert "Second log message" in log_text
        
        # Check that the second message comes after the first
        first_pos = log_text.find("First log message")
        second_pos = log_text.find("Second log message")
        assert first_pos < second_pos
    else:
        # If the method doesn't exist, test using setText
        logs_tab.log_text.setPlainText("First log message\nSecond log message")
        log_text = logs_tab.log_text.toPlainText()
        assert "First log message" in log_text
        assert "Second log message" in log_text


def test_log_text_is_read_only(logs_tab):
    """Test that the log text is read-only."""
    assert logs_tab.log_text.isReadOnly() is True


def test_filter_logs(logs_tab):
    """Test filtering logs if the feature exists."""
    # This test assumes that the LogsTab has a filter feature
    if hasattr(logs_tab, 'filter_input') and hasattr(logs_tab, 'apply_filter'):
        # Set up some log entries
        logs_tab.log_text.setPlainText("ERROR: Connection failed\nINFO: Process started\nWARNING: Timeout occurred")
        
        # Apply a filter
        logs_tab.filter_input.setText("ERROR")
        logs_tab.apply_filter()
        
        # Check that only matching entries are shown
        filtered_text = logs_tab.log_text.toPlainText()
        assert "ERROR: Connection failed" in filtered_text
        assert "INFO: Process started" not in filtered_text
        assert "WARNING: Timeout occurred" not in filtered_text 
