#!/usr/bin/env python3
"""
Script to run interfaces.pyqt.DreamOsMainWindow with proper sip handling.

This script:
1. Creates a dummy sip module and installs it in sys.modules
2. Configures necessary attributes to prevent import errors
3. Then runs the DreamOsMainWindow module

Usage:
    python run_pyqt_without_sip.py
"""

import sys
import types
import importlib
import runpy
import logging
import builtins

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def patch_sip():
    """
    Create a proper dummy sip module and install it.
    """
    logger.info("Setting up dummy sip module")
    
    # Create dummy sip module
    dummy_sip = types.ModuleType('sip')
    
    # Add attributes that PyQt5 expects
    dummy_sip.setapi = lambda *args, **kwargs: None
    dummy_sip.SIP_VERSION = "0.0.0"
    dummy_sip.SIP_VERSION_STR = "0.0.0"
    dummy_sip.wrapinstance = lambda ptr, type: None
    dummy_sip._C_API = object()  # Use a real object, not None
    
    # Install the dummy sip module
    sys.modules['sip'] = dummy_sip
    logger.info("Dummy sip module installed")
    
    # Make PyQt5.sip point to our dummy module
    sys.modules['PyQt5.sip'] = dummy_sip
    
    # Patch the import system to handle PyQt5 imports
    original_import = builtins.__import__
    
    def patched_import(name, *args, **kwargs):
        """Custom import function to handle sip-related imports."""
        # Check if it's a sip-related import
        if name == 'sip' or name == 'PyQt5.sip':
            return dummy_sip
        
        # Otherwise, use the original import
        module = original_import(name, *args, **kwargs)
        
        # If PyQt5 is being imported, ensure it has a sip attribute
        if name == 'PyQt5' and not hasattr(module, 'sip'):
            module.sip = dummy_sip
            logger.info("Added sip reference to dynamically imported PyQt5")
            
        return module
    
    # Install the patched import function
    builtins.__import__ = patched_import
    
    # If PyQt5 is already imported, add sip to it
    if 'PyQt5' in sys.modules:
        sys.modules['PyQt5'].sip = dummy_sip
        logger.info("Added sip to existing PyQt5 module")
    
    return True

def main():
    """Main entry point."""
    logger.info("Starting run_pyqt_without_sip.py")
    
    # Apply the sip patch
    if not patch_sip():
        logger.error("Failed to patch sip module")
        return 1
    
    # Verify path
    logger.info(f"Python path: {sys.path}")
    
    # Prepare error list
    errors = []
    
    # Try running the module directly
    target_module = 'interfaces.pyqt.DreamOsMainWindow'
    logger.info(f"Attempting to run {target_module}")
    
    try:
        # Run the main module
        runpy.run_module(target_module, run_name='__main__')
        return 0
    except Exception as e:
        errors.append(f"Error running as module: {str(e)}")
        logger.error(f"Error running {target_module}: {e}")
        import traceback
        traceback.print_exc()
        
    # If module running failed, try direct import
    try:
        logger.info("Attempting direct import...")
        from interfaces.pyqt.DreamOsMainWindow import main
        main()
        return 0
    except Exception as e:
        errors.append(f"Error with direct import: {str(e)}")
        logger.error(f"Error with direct import: {e}")
        traceback.print_exc()
    
    # If all approaches failed, report detailed errors
    logger.error("All approaches failed. Errors:")
    for i, error in enumerate(errors, 1):
        logger.error(f"{i}. {error}")
    
    return 1

if __name__ == "__main__":
    sys.exit(main()) 