#!/usr/bin/env python
"""
Mocked test for MeredithTab.

This script tests the MeredithTab class using mock dependencies.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication

# Create a QApplication instance for the test
app = QApplication([])

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Import and initialize mocks before importing the actual module
from tests.gui.tabs.mocks.mock_meredith_dependencies import *

# Now import the MeredithTab
from interfaces.pyqt.tabs.meredith_tab import MeredithTab

class MeredithTabTests(unittest.TestCase):
    """Tests for the MeredithTab component."""
    
    def setUp(self):
        """Set up the test environment."""
        self.tab = MeredithTab(private_mode=False)
    
    def test_ui_initialization(self):
        """Test that the UI components are initialized correctly."""
        self.assertEqual(self.tab.run_button.text(), "Run Full Scan")
        self.assertFalse(self.tab.stop_button.isEnabled())
        self.assertEqual(self.tab.results_table.columnCount(), 8)
        self.assertEqual(self.tab.results_table.horizontalHeaderItem(0).text(), "Platform")
        self.assertEqual(self.tab.results_table.horizontalHeaderItem(1).text(), "Username")
        self.assertEqual(self.tab.results_table.horizontalHeaderItem(7).text(), "Resonance Score")
        print("✅ UI initialization test passed")
    
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
        print("✅ Clear results test passed")
    
    def test_log_message_updates_text_edit(self):
        """Test that the log function updates the text edit with a message."""
        # Setup: Create a test message
        test_message = "Test log message"
        
        # Act: Log the message
        self.tab.log(test_message)
        
        # Assert: The message was added to the log
        self.assertIn(test_message, self.tab.log_output.toPlainText())
        print("✅ Log message test passed")

if __name__ == '__main__':
    print("Running mocked tests for MeredithTab...")
    unittest.main() 
