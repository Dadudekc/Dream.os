"""
SIP Patcher - Creates mock SIP modules to prevent import errors

This module creates a mock 'sip' module and ensures that 'PyQt5.sip' imports 
work properly. This is necessary because PyQt5-sip is now included with PyQt5,
and explicit sip imports can cause errors in some Python configurations.
"""

import sys
import types
import logging
import importlib
import builtins
import ctypes

logger = logging.getLogger(__name__)

def patch_sip_imports():
    """
    Create mock sip modules to prevent import errors.
    Should be called before any PyQt5 imports.
    
    This function:
    1. Creates a dummy 'sip' module if it doesn't exist
    2. Ensures 'PyQt5.sip' can be imported
    """
    logger.info("Patching sip imports")
    
    # Try to import the real PyQt5.sip first
    try:
        import PyQt5.sip as real_sip
        logger.info("Successfully imported real PyQt5.sip")
        
        # If we've got the real sip, use it
        if 'sip' not in sys.modules:
            sys.modules['sip'] = real_sip
            logger.info("Set sys.modules['sip'] to real PyQt5.sip")
        
        return True
    except (ImportError, AttributeError) as e:
        logger.warning(f"Cannot import real PyQt5.sip: {e}. Creating dummy version.")
    
    # Create a dummy sip module
    if 'sip' not in sys.modules:
        dummy_sip = types.ModuleType('sip')
        
        # Add attributes that might be used
        dummy_sip.setapi = lambda *args, **kwargs: None
        dummy_sip.SIP_VERSION = "0.0.0"
        dummy_sip.SIP_VERSION_STR = "0.0.0"
        dummy_sip.wrapinstance = lambda ptr, type: None
        
        # Important: Create the _C_API attribute with proper type
        # The _C_API attribute needs to be a ctypes pointer type to work
        try:
            dummy_sip._C_API = ctypes.c_void_p(0)  # Use a proper C pointer type
        except Exception as e:
            logger.error(f"Failed to create _C_API attribute: {e}")
            dummy_sip._C_API = object()  # Fallback
        
        # Register it in sys.modules
        sys.modules['sip'] = dummy_sip
        logger.info("Created dummy 'sip' module")
    
    # If PyQt5 is imported, add a reference to sip
    if 'PyQt5' in sys.modules:
        PyQt5 = sys.modules['PyQt5']
        if not hasattr(PyQt5, 'sip'):
            PyQt5.sip = sys.modules['sip']
            logger.info("Added sip reference to PyQt5 module")
    else:
        # If PyQt5 isn't imported yet, try importing it safely
        try:
            orig_modules = sys.modules.copy()
            PyQt5 = importlib.import_module('PyQt5')
            if not hasattr(PyQt5, 'sip'):
                PyQt5.sip = sys.modules['sip']
                logger.info("Added sip reference to newly imported PyQt5 module")
        except Exception as e:
            logger.warning(f"Could not pre-import PyQt5: {e}")
            # Restore modules if import failed
            sys.modules = orig_modules
    
    # Register PyQt5.sip for direct imports
    if 'PyQt5.sip' not in sys.modules:
        sys.modules['PyQt5.sip'] = sys.modules['sip']
        logger.info("Registered PyQt5.sip in sys.modules")
    
    # Monkey-patch the import system to handle dynamic imports
    original_import = builtins.__import__
    
    def patched_import(name, *args, **kwargs):
        """Custom import function to handle sip-related imports."""
        # Check if it's a sip-related import
        if name == 'sip' or name == 'PyQt5.sip':
            return sys.modules['sip']
        
        # Otherwise, use the original import
        module = original_import(name, *args, **kwargs)
        
        # If PyQt5 is being imported, ensure it has a sip attribute
        if name == 'PyQt5' and not hasattr(module, 'sip'):
            module.sip = sys.modules['sip']
            logger.info("Added sip reference to dynamically imported PyQt5")
            
        return module
    
    # Install the patched import function
    builtins.__import__ = patched_import
    
    return True 