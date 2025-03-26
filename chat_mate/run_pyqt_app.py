#!/usr/bin/env python3
"""
Wrapper script to run the PyQt application with proper sip handling.

This script:
1. Properly sets up the Python environment to handle sip imports
2. Then runs the PyQt application

Usage:
    python run_pyqt_app.py
"""

import sys
import types
import importlib
import runpy

def patch_sip_imports():
    """
    Create a proper dummy sip module if needed.
    Must be called before any PyQt imports.
    """
    print("Patching sip imports for PyQt5 compatibility...")
    
    # Create a dummy sip module if it doesn't exist
    if 'sip' not in sys.modules:
        dummy_sip = types.ModuleType('sip')
        
        # Add attributes that might be used
        dummy_sip.setapi = lambda *args, **kwargs: None
        dummy_sip.SIP_VERSION = "0.0.0"
        dummy_sip.SIP_VERSION_STR = "0.0.0"
        dummy_sip.wrapinstance = lambda ptr, type: None
        
        # Important: Create the _C_API attribute that PyQt5 expects
        dummy_sip._C_API = None
        
        # Register it in sys.modules
        sys.modules['sip'] = dummy_sip
        print("Created dummy 'sip' module")
    
    # Make sure PyQt5.sip is available
    if 'PyQt5.sip' not in sys.modules:
        if 'PyQt5' not in sys.modules:
            # Import PyQt5 first
            try:
                importlib.import_module('PyQt5')
                print("Imported PyQt5")
            except ImportError as e:
                print(f"Error importing PyQt5: {e}")
                return False
        
        # Now setup PyQt5.sip
        sys.modules['PyQt5.sip'] = sys.modules['sip']
        if hasattr(sys.modules['PyQt5'], '__path__'):
            # If PyQt5 is a package, ensure it has sip
            sys.modules['PyQt5'].sip = sys.modules['sip']
            print("Added sip reference to PyQt5 module")
    
    return True

def main():
    """Main entry point."""
    print("Setting up environment for PyQt5...")
    
    # Patch sip imports before anything else
    if not patch_sip_imports():
        print("Error setting up sip patching. Exiting.")
        return 1
    
    print("Starting PyQt application...")
    
    try:
        # Run the __main__.py in interfaces.pyqt
        runpy.run_module('interfaces.pyqt', run_name='__main__')
        return 0
    except Exception as e:
        print(f"Error running PyQt application: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 