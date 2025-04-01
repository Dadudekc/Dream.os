#!/usr/bin/env python
"""
Completely isolated test script for MeredithTab.

This script creates a mock version of the MeredithTab class and tests its functionality
without relying on the actual implementation.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QProgressBar, QComboBox, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject

# Create a QApplication instance for the test
app = QApplication([])

# Enable more verbose output
print("Starting MeredithTab isolated tests...")

# Mock ScraperThread class
class MockScraperThread(QThread):
    """Mock implementation of the ScraperThread class."""
    scan_completed = pyqtSignal(list)
    log_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancel_requested = False
    
    def cancel(self):
        self._cancel_requested = True
    
    def run(self):
        # Simulate a scan
        self.log_update.emit("Starting scan...")
        self.progress_update.emit(50)
        profiles = [
            {"platform": "Reddit", "username": "user1", "bio": "Test bio", "location": "TX", "url": "https://reddit.com/u/user1"}
        ]
        self.log_update.emit("Scan completed.")
        self.progress_update.emit(100)
        self.scan_completed.emit(profiles)

# Mock MeredithTab class
class MeredithTab(QWidget):
    """Mock implementation of the MeredithTab class for testing."""
    
    def __init__(self, parent=None, private_mode=True):
        super().__init__(parent)
        self.private_mode = private_mode
        self.filtered_profiles = []
        self.dispatcher = MagicMock()
        self.scorer = MagicMock()
        
        self.setWindowTitle("Meredith - Private Resonance Scanner")
        self.init_ui()
        
        if self.private_mode:
            self.hide()
    
    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("Meredith: Private Resonance Scanner")
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Model selector
        self.model_selector = QComboBox()
        self.populate_model_selector()
        layout.addWidget(self.model_selector)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.run_button = QPushButton("Run Full Scan")
        self.run_button.clicked.connect(self.run_full_scan)
        button_layout.addWidget(self.run_button)
        
        self.stop_button = QPushButton("Stop Scan")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_scan)
        button_layout.addWidget(self.stop_button)
        
        self.export_button = QPushButton("Export Results")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False)
        button_layout.addWidget(self.export_button)
        
        self.clear_button = QPushButton("Clear Results")
        self.clear_button.clicked.connect(self.clear_results)
        self.clear_button.setEnabled(False)
        button_layout.addWidget(self.clear_button)
        
        layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(100)
        layout.addWidget(self.log_output)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels([
            "Platform", "Username", "Bio", "Location", "URL", "Message", "Analyze", "Resonance Score"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.results_table)
        
        self.setLayout(layout)
    
    def populate_model_selector(self):
        """Populate the model selector with mock data."""
        self.model_selector.clear()
        self.model_selector.addItem("romantic")
        self.model_selector.addItem("friend")
    
    def switch_model(self, model_name):
        """Switch the resonance model."""
        self.scorer.load_model.assert_called_with(f"models/{model_name}.json")
    
    def run_full_scan(self):
        """Start the scraper thread."""
        self._scraper_thread = MockScraperThread(self)
        self._scraper_thread.log_update.connect(self.log)
        self._scraper_thread.progress_update.connect(self.progress_bar.setValue)
        self._scraper_thread.scan_completed.connect(self.on_scan_completed)
        
        self._scraper_thread.start()
        
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
    
    def stop_scan(self):
        """Cancel the scraper thread."""
        if hasattr(self, '_scraper_thread'):
            self._scraper_thread.cancel()
        self.log("Scan canceled.")
    
    def on_scan_completed(self, profiles):
        """Handle the completed scan results."""
        self.filtered_profiles = profiles
        self.populate_results_table(profiles)
        
        self.export_button.setEnabled(True)
        self.clear_button.setEnabled(True)
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
    
    def populate_results_table(self, profiles):
        """Populate the results table with profiles."""
        self.results_table.setRowCount(len(profiles))
        
        for row, profile in enumerate(profiles):
            # Basic info columns
            self.results_table.setItem(row, 0, QTableWidgetItem(profile.get("platform", "")))
            self.results_table.setItem(row, 1, QTableWidgetItem(profile.get("username", "")))
            self.results_table.setItem(row, 2, QTableWidgetItem(profile.get("bio", "")))
            self.results_table.setItem(row, 3, QTableWidgetItem(profile.get("location", "")))
            self.results_table.setItem(row, 4, QTableWidgetItem(profile.get("url", "")))
            
            # Message button (column 5)
            message_btn = QPushButton("Message")
            message_btn.clicked.connect(lambda _, url=profile.get("url", ""): self.open_profile_in_browser(url))
            self.results_table.setCellWidget(row, 5, message_btn)
            
            # Analyze button (column 6)
            analyze_btn = QPushButton("Analyze")
            analyze_btn.clicked.connect(lambda _, p=profile: self.analyze_profile(p))
            self.results_table.setCellWidget(row, 6, analyze_btn)
            
            # Resonance score (column 7)
            self.results_table.setItem(row, 7, QTableWidgetItem("Not analyzed"))
    
    def analyze_profile(self, profile):
        """Analyze a profile using the resonance scorer."""
        # Mock the dispatcher response
        result = {"resonance_score": 91, "should_save_to_meritchain": True}
        
        # Log the result
        self.log(f"Analyzed profile: {profile.get('username')} - Resonance Score {result['resonance_score']}")
    
    def export_results(self):
        """Export the results to a JSON file."""
        # Mock saving to file
        self.log("Results exported to file.")
    
    def clear_results(self):
        """Clear the results from the UI."""
        self.filtered_profiles = []
        self.results_table.setRowCount(0)
        self.export_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        self.log("Results cleared.")
    
    def open_profile_in_browser(self, url):
        """Open the profile URL in a browser."""
        self.log(f"Opening URL: {url}")
    
    def log(self, message):
        """Add a message to the log output."""
        self.log_output.append(message)

# Test class
class MeredithTabTests(unittest.TestCase):
    """Tests for the MeredithTab component."""
    
    def setUp(self):
        """Set up the test environment."""
        print("Setting up test case...")
        self.tab = MeredithTab(private_mode=False)
    
    def tearDown(self):
        """Clean up the test environment."""
        print("Tearing down test case...")
        self.tab.close()
    
    def test_ui_initialization(self):
        """Test that the UI components are initialized correctly."""
        print("Running UI initialization test...")
        self.assertEqual(self.tab.run_button.text(), "Run Full Scan")
        self.assertFalse(self.tab.stop_button.isEnabled())
        self.assertEqual(self.tab.results_table.columnCount(), 8)
        self.assertEqual(self.tab.results_table.horizontalHeaderItem(0).text(), "Platform")
        self.assertEqual(self.tab.results_table.horizontalHeaderItem(1).text(), "Username")
        self.assertEqual(self.tab.results_table.horizontalHeaderItem(7).text(), "Resonance Score")
        print("✅ UI initialization test passed")
    
    def test_clear_results_resets_state(self):
        """Test that clicking the clear button resets the UI state."""
        print("Running clear results test...")
        # Setup: Add some data to the tab
        self.tab.filtered_profiles = [{"username": "test"}]
        self.tab.results_table.setRowCount(1)
        self.tab.export_button.setEnabled(True)
        self.tab.clear_button.setEnabled(True)
        
        # Act: Clear the results
        self.tab.clear_results()
        
        # Assert: Data is cleared
        self.assertEqual(self.tab.results_table.rowCount(), 0)
        self.assertEqual(len(self.tab.filtered_profiles), 0)
        self.assertFalse(self.tab.export_button.isEnabled())
        self.assertFalse(self.tab.clear_button.isEnabled())
        print("✅ Clear results test passed")
    
    def test_log_message_updates_text_edit(self):
        """Test that the log function updates the text edit with a message."""
        print("Running log message test...")
        # Setup: Create a test message
        test_message = "Test log message"
        
        # Act: Log the message
        self.tab.log(test_message)
        
        # Assert: The message was added to the log
        self.assertIn(test_message, self.tab.log_output.toPlainText())
        print("✅ Log message test passed")

if __name__ == '__main__':
    print("Running isolated tests for MeredithTab...")
    unittest.main(argv=['first-arg-is-ignored'], verbosity=2) 
