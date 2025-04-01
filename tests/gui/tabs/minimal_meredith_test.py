#!/usr/bin/env python
"""
Minimal standalone test for MeredithTab.

This script directly tests just the most basic functionality of the MeredithTab class.
"""

import os
import sys
import unittest
from PyQt5.QtWidgets import QApplication

# Create a QApplication instance for the test
app = QApplication([])

# Test class
class MeredithTabBasicTest(unittest.TestCase):
    """Minimal test for the MeredithTab component."""
    
    def test_meredith_tab_exists(self):
        """Test that the MeredithTab module can be imported."""
        # Add the project root to the path
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
        
        try:
            # Import the MeredithTab class directly from the file
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../interfaces/pyqt/tabs')))
            import meredith_tab
            from meredith_tab import MeredithTab
            
            # Create an instance to verify it works
            tab = MeredithTab(private_mode=False)
            
            # Verify some basic properties
            self.assertEqual(tab.windowTitle(), "Meredith - Private Resonance Scanner")
            self.assertTrue(hasattr(tab, 'run_button'))
            self.assertTrue(hasattr(tab, 'stop_button'))
            self.assertTrue(hasattr(tab, 'results_table'))
            
            # Check run button text
            self.assertEqual(tab.run_button.text(), "Run Full Scan")
            
            # Test passed
            print("✅ Successfully imported and instantiated MeredithTab")
            
        except ImportError as e:
            self.fail(f"Failed to import MeredithTab: {e}")
        except Exception as e:
            self.fail(f"Failed to create MeredithTab instance: {e}")

if __name__ == '__main__':
    print("Running minimal test for MeredithTab...")
    unittest.main() 
