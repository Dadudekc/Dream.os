"""
Diagnostic script to debug PyQt interface initialization in run_app.py.
This helps identify why the GUI window doesn't appear.
"""

import os
import sys
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug_pyqt.log", mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PyQtDebug")

def test_pyqt_basics():
    """Test if basic PyQt functionality works."""
    logger.info("Testing basic PyQt functionality...")
    try:
        from PyQt5.QtWidgets import QApplication, QLabel
        app = QApplication(sys.argv)
        label = QLabel("PyQt5 basic test")
        logger.info("Basic PyQt imports and objects created successfully")
        return True
    except Exception as e:
        logger.error(f"PyQt5 basic test failed: {e}")
        traceback.print_exc()
        return False

def test_main_window_import():
    """Test if DreamOsMainWindow can be imported."""
    logger.info("Testing DreamOsMainWindow import...")
    try:
        from interfaces.pyqt.DreamOsMainWindow import DreamOsMainWindow
        logger.info("DreamOsMainWindow imported successfully")
        return True
    except Exception as e:
        logger.error(f"DreamOsMainWindow import failed: {e}")
        traceback.print_exc()
        return False

def test_interfaces_main_import():
    """Test if interfaces.pyqt.__main__ can be imported."""
    logger.info("Testing interfaces.pyqt.__main__ import...")
    try:
        from interfaces.pyqt.__main__ import main as pyqt_main
        logger.info("interfaces.pyqt.__main__.main imported successfully")
        return True
    except Exception as e:
        logger.error(f"interfaces.pyqt.__main__ import failed: {e}")
        traceback.print_exc()
        return False

def trace_execution():
    """Trace actual execution through run_app.py with additional debug points."""
    logger.info("Tracing execution through run_app.py...")
    
    try:
        # Log Python environment info
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Python executable: {sys.executable}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
        logger.info(f"sys.path: {sys.path}")
        
        # Import and run the application with debug points
        logger.info("Importing PyQt interface...")
        from interfaces.pyqt.__main__ import main as pyqt_main
        
        logger.info("About to call pyqt_main()...")
        
        # Monkey patch QApplication to track window creation
        logger.info("Monkey patching QApplication to track window creation...")
        import PyQt5.QtWidgets
        original_show = PyQt5.QtWidgets.QWidget.show
        
        def show_with_logging(self):
            logger.info(f"Window {self.__class__.__name__} is being shown")
            return original_show(self)
        
        PyQt5.QtWidgets.QWidget.show = show_with_logging
        
        # Create custom QApplication to track when exec_ is called
        original_QApplication = PyQt5.QtWidgets.QApplication
        
        class DebugQApplication(original_QApplication):
            def exec_(self):
                logger.info("QApplication.exec_() called")
                return super().exec_()
        
        PyQt5.QtWidgets.QApplication = DebugQApplication
        
        logger.info("Starting PyQt interface with debugging...")
        result = pyqt_main()
        logger.info(f"PyQt interface main() returned: {result}")
        return result
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error(f"Import error traceback:\n{traceback.format_exc()}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(f"Error traceback:\n{traceback.format_exc()}")
        return 1

def main():
    """Run diagnostic tests."""
    logger.info("Starting PyQt diagnostic tests")
    
    # Test basic PyQt functionality
    if not test_pyqt_basics():
        logger.critical("Basic PyQt functionality test failed. Cannot continue.")
        return 1
    
    # Test importing main components
    if not test_main_window_import():
        logger.warning("DreamOsMainWindow import failed. This could prevent the app from starting.")
    
    if not test_interfaces_main_import():
        logger.warning("interfaces.pyqt.__main__ import failed. This could prevent the app from starting.")
    
    # Trace execution
    logger.info("Starting execution trace...")
    return trace_execution()

if __name__ == "__main__":
    sys.exit(main()) 