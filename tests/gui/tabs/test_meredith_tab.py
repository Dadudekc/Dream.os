"""
Test module for the MeredithTab component.

Tests the functionality of the MeredithTab class, including:
- UI initialization
- ScraperThread logic
- Button behavior
- Table rendering
- Dispatcher integration
- Export and clear functionality
- Model switching
"""

import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication, QTableWidgetItem

# Add the root directory to the path so we can import from interfaces
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from interfaces.pyqt.tabs.meredith_tab import MeredithTab, ScraperThread

# Define fixtures for testing
@pytest.fixture(scope="module")
def app():
    """Create a QApplication instance for the tests."""
    if not QApplication.instance():
        return QApplication([])
    return QApplication.instance()

@pytest.fixture
def tab(qtbot):
    """Create a MeredithTab instance and add it to qtbot."""
    tab = MeredithTab(private_mode=False)
    qtbot.addWidget(tab)
    return tab

def test_ui_initialization(tab):
    """Test that the UI components are initialized correctly."""
    assert tab.run_button.text() == "Run Full Scan"
    assert tab.stop_button.isEnabled() is False
    assert tab.results_table.columnCount() == 8
    assert tab.results_table.horizontalHeaderItem(0).text() == "Platform"
    assert tab.results_table.horizontalHeaderItem(1).text() == "Username"
    assert tab.results_table.horizontalHeaderItem(7).text() == "Resonance Score"

def test_model_selector_loads_models(monkeypatch, tab):
    """Test that the model selector loads available resonance models."""
    monkeypatch.setattr("os.listdir", lambda _: ["romantic.json", "friend.json"])
    tab.populate_model_selector()
    models = [tab.model_selector.itemText(i) for i in range(tab.model_selector.count())]
    assert "romantic" in models
    assert "friend" in models

@patch("interfaces.pyqt.tabs.meredith_tab.ScraperThread")
def test_run_full_scan_starts_thread(mock_thread, tab):
    """Test that clicking the run button starts the scraper thread."""
    mock_instance = mock_thread.return_value
    tab.run_full_scan()
    
    mock_instance.start.assert_called_once()
    assert not tab.run_button.isEnabled()
    assert tab.stop_button.isEnabled()

def test_stop_scan_cancels_thread(tab):
    """Test that clicking the stop button cancels the scraper thread."""
    # Create a mock thread and attach it to the tab
    mock_thread = MagicMock()
    tab._scraper_thread = mock_thread
    tab.stop_button.setEnabled(True)
    
    # Call the stop_scan method
    tab.stop_scan()
    
    # Verify the cancel method was called
    mock_thread.cancel.assert_called_once()

def test_clear_results_resets_state(tab):
    """Test that clicking the clear button resets the UI state."""
    # Setup: Add some data to the tab
    tab.filtered_profiles = [{"username": "test"}]
    tab.results_table.setRowCount(1)
    tab.export_button.setEnabled(True)
    tab.clear_button.setEnabled(True)
    
    # Act: Clear the results
    tab.clear_results()
    
    # Assert: Data is cleared
    assert tab.results_table.rowCount() == 0
    assert not tab.filtered_profiles
    assert not tab.export_button.isEnabled()
    assert not tab.clear_button.isEnabled()

def test_export_results_creates_file(tmp_path, qtbot, tab, monkeypatch):
    """Test that the export function creates a JSON file with profile data."""
    # Setup: Add a profile to export
    profile = {"platform": "Reddit", "username": "ethereal_logic"}
    tab.filtered_profiles = [profile]
    tab.export_button.setEnabled(True)

    # Simulate user picking a file path
    path = tmp_path / "out.json"
    monkeypatch.setattr("PyQt5.QtWidgets.QFileDialog.getSaveFileName", 
                        lambda *a, **kw: (str(path), None))

    # Act: Export the results
    tab.export_results()
    
    # Assert: File was created with the expected content
    assert path.exists()
    with open(path) as f:
        assert "ethereal_logic" in f.read()

@patch("core.meredith.meredith_dispatcher.MeredithDispatcher.process_profile")
def test_analyze_profile_updates_score(mock_process, tab):
    """Test that the analyze function updates the resonance score in the UI."""
    # Setup: Mock the dispatcher's process_profile method
    mock_process.return_value = {
        "resonance_score": 91,
        "should_save_to_meritchain": True
    }
    
    # Create a profile to analyze
    profile = {
        "platform": "Reddit",
        "username": "ethereal_logic",
        "bio": "Soft energy",
        "location": "TX",
        "url": "https://reddit.com/u/ethereal_logic"
    }
    tab.filtered_profiles = [profile]
    
    # Act: Analyze the profile
    tab.analyze_profile(profile)
    
    # Assert: The log shows the score and the dispatcher was called
    assert "Resonance Score 91" in tab.log_output.toPlainText()
    mock_process.assert_called_once()

@patch("interfaces.pyqt.tabs.meredith_tab.ResonanceScorer")
def test_switch_model_loads_model(mock_scorer, tab):
    """Test that switching the model loads the new resonance model."""
    # Setup: Mock the ResonanceScorer and its load_model method
    mock_instance = mock_scorer.return_value
    tab.scorer = mock_instance
    
    # Act: Switch the model
    tab.switch_model("professional")
    
    # Assert: The model was loaded with the correct path
    mock_instance.load_model.assert_called_once()
    model_path = mock_instance.load_model.call_args[0][0]
    assert "professional.json" in model_path

@patch("webbrowser.open")
def test_open_profile_in_browser(mock_open, tab):
    """Test that the open_profile_in_browser function opens the URL in a browser."""
    # Setup: Define a URL to open
    test_url = "https://reddit.com/u/test_user"
    
    # Act: Open the profile
    tab.open_profile_in_browser(test_url)
    
    # Assert: The browser was opened with the correct URL
    mock_open.assert_called_once_with(test_url)

def test_on_scan_completed_updates_ui(tab):
    """Test that the on_scan_completed function updates the UI with profiles."""
    # Setup: Create test profiles
    profiles = [
        {"platform": "Reddit", "username": "user1", "bio": "Test bio", "location": "TX", "url": "https://reddit.com/u/user1"}
    ]
    
    # Act: Process the completed scan
    tab.on_scan_completed(profiles)
    
    # Assert: UI was updated
    assert tab.filtered_profiles == profiles
    assert tab.export_button.isEnabled()
    assert tab.clear_button.isEnabled()
    assert tab.results_table.rowCount() == 1
    
def test_populate_results_table(tab):
    """Test that the populate_results_table function correctly fills the table."""
    # Setup: Create test profiles
    profiles = [
        {"platform": "Reddit", "username": "user1", "bio": "Test bio", "location": "TX", "url": "https://reddit.com/u/user1"}
    ]
    
    # Act: Populate the table
    tab.populate_results_table(profiles)
    
    # Assert: Table was populated correctly
    assert tab.results_table.rowCount() == 1
    assert tab.results_table.item(0, 0).text() == "Reddit"
    assert tab.results_table.item(0, 1).text() == "user1"
    assert tab.results_table.item(0, 2).text() == "Test bio"
    assert tab.results_table.item(0, 3).text() == "TX"
    
    # Check that buttons were created in columns 5 and 6
    message_btn_cell = tab.results_table.cellWidget(0, 5)
    analyze_btn_cell = tab.results_table.cellWidget(0, 6)
    assert message_btn_cell is not None
    assert analyze_btn_cell is not None

@patch("interfaces.pyqt.tabs.meredith_tab.QMessageBox")
def test_log_message_updates_text_edit(mock_msg_box, tab):
    """Test that the log function updates the text edit with a message."""
    # Setup: Create a test message
    test_message = "Test log message"
    
    # Act: Log the message
    tab.log(test_message)
    
    # Assert: The message was added to the log
    assert test_message in tab.log_output.toPlainText() 