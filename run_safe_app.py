"""
Script to run the Dream.OS PyQt interface with enhanced error handling.
"""

import os
import sys as python_sys
import logging
import traceback
from pathlib import Path

# Import the LoggerFactory
from core.logging.factories.LoggerFactory import LoggerFactory

def main():
    """Run the Dream.OS PyQt interface with enhanced error handling."""
    # Get logger using the factory
    # Note: Log file will be in outputs/logs/run_app.log
    logger = LoggerFactory.create_standard_logger(
        name="run_safe_app", 
        level=logging.DEBUG, 
        log_to_file=True
    )

    try:
        # Log Python environment info
        logger.info(f"Python version: {python_sys.version}")
        logger.info(f"Python executable: {python_sys.executable}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
        
        # First try importing PyQt to check if it works
        logger.info("Testing PyQt import...")
        from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
        logger.info("PyQt imports successful.")
        
        # Create a basic application with a fallback mode
        app = QApplication(python_sys.argv)
        
        # Try importing and running the application with custom error handling
        try:
            logger.info("Importing PyQt interface...")
            from interfaces.pyqt.__main__ import main as pyqt_main
            
            # Create an error handler for uncaught exceptions
            def exception_hook(exctype, value, traceback_obj):
                logger.critical(f"Uncaught exception: {exctype} - {value}")
                logger.critical("".join(traceback.format_tb(traceback_obj)))
                # Show error message to user
                from PyQt5.QtWidgets import QMessageBox
                error_box = QMessageBox()
                error_box.setIcon(QMessageBox.Critical)
                error_box.setText("An error occurred in the application")
                error_box.setInformativeText(f"{exctype.__name__}: {value}")
                error_box.setWindowTitle("Dream.OS Error")
                error_box.setDetailedText("".join(traceback.format_tb(traceback_obj)))
                error_box.exec_()
            
            # Install the custom exception handler
            python_sys.excepthook = exception_hook
            
            logger.info("Starting PyQt interface...")
            return pyqt_main()
            
        except ImportError as e:
            logger.error(f"Failed to import Dream.OS main window: {e}")
            logger.error(traceback.format_exc())
            
            # Create and show a fallback window instead
            logger.info("Initializing fallback window...")
            
            # Create main window
            window = QMainWindow()
            window.setWindowTitle("Dream.OS (Safe Mode)")
            window.setGeometry(100, 100, 800, 600)
            
            # Create central widget and layout
            central_widget = QWidget()
            window.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            
            # Add information about the error
            error_label = QLabel(f"Failed to load the main application: {e}")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)
            
            info_label = QLabel(
                "The application is running in safe mode. Please check the logs for more information."
            )
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
            
            # Display the window
            window.show()
            logger.info("Fallback window displayed")
            
            # Run the application
            return app.exec_()
        
    except ImportError as e:
        logger.error(f"Critical import error: {e}")
        logger.error(f"Import error traceback:\n{traceback.format_exc()}")
        print(f"ERROR: Failed to initialize application: {e}")
        print("See log file for details.")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(f"Error traceback:\n{traceback.format_exc()}")
        print(f"ERROR: Unexpected error: {e}")
        print("See log file for details.")
        return 1

if __name__ == '__main__':
    python_sys.exit(main()) 