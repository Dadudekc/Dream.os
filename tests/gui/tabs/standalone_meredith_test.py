#!/usr/bin/env python
"""
Standalone test script for MeredithTab.

This script directly tests the MeredithTab class without relying on the existing test infrastructure.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Create a QApplication instance for the test
app = QApplication([])

# Import the MeredithTab class
from interfaces.pyqt.tabs.meredith_tab import MeredithTab, ScraperThread

class MeredithTabTests(unittest.TestCase):
    """Tests for the MeredithTab component."""
    
    def setUp(self):
        """Set up the test environment."""
        self.tab = MeredithTab(private_mode=False)
    
    def tearDown(self):
        """Clean up the test environment."""
        self.tab.deleteLater()
    
    def test_ui_initialization(self):
        """Test that the UI components are initialized correctly."""
        self.assertEqual(self.tab.run_button.text(), "Run Full Scan")
        self.assertFalse(self.tab.stop_button.isEnabled())
        self.assertEqual(self.tab.results_table.columnCount(), 8)
        self.assertEqual(self.tab.results_table.horizontalHeaderItem(0).text(), "Platform")
        self.assertEqual(self.tab.results_table.horizontalHeaderItem(1).text(), "Username")
        self.assertEqual(self.tab.results_table.horizontalHeaderItem(7).text(), "Resonance Score")
    
    @patch('os.listdir')
    def test_model_selector_loads_models(self, mock_listdir):
        """Test that the model selector loads available resonance models."""
        mock_listdir.return_value = ["romantic.json", "friend.json"]
        self.tab.populate_model_selector()
        
        models = [self.tab.model_selector.itemText(i) for i in range(self.tab.model_selector.count())]
        self.assertIn("romantic", models)
        self.assertIn("friend", models)
    
    @patch('interfaces.pyqt.tabs.meredith_tab.ScraperThread')
    def test_run_full_scan_starts_thread(self, mock_thread_class):
        """Test that clicking the run button starts the scraper thread."""
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread
        
        self.tab.run_full_scan()
        
        mock_thread.start.assert_called_once()
        self.assertFalse(self.tab.run_button.isEnabled())
        self.assertTrue(self.tab.stop_button.isEnabled())
    
    def test_stop_scan_cancels_thread(self):
        """Test that clicking the stop button cancels the scraper thread."""
        # Create a mock thread and attach it to the tab
        mock_thread = MagicMock()
        self.tab._scraper_thread = mock_thread
        self.tab.stop_button.setEnabled(True)
        
        # Call the stop_scan method
        self.tab.stop_scan()
        
        # Verify the cancel method was called
        mock_thread.cancel.assert_called_once()
    
    def test_clear_results_resets_state(self):
        """Test that clicking the clear button resets the UI state."""
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
    
    def test_log_message_updates_text_edit(self):
        """Test that the log function updates the text edit with a message."""
        # Setup: Create a test message
        test_message = "Test log message"
        
        # Act: Log the message
        self.tab.log(test_message)
        
        # Assert: The message was added to the log
        self.assertIn(test_message, self.tab.log_output.toPlainText())

if __name__ == '__main__':
    print("Running standalone tests for MeredithTab...")
    unittest.main() 