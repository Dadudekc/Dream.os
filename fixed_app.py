"""
Script to run the Dream.OS PyQt interface with WebEngine support and explicit window display.
"""

import os
import sys
import logging
import traceback

# Import the LoggerFactory
from core.logging.factories.LoggerFactory import LoggerFactory

# Import PyQt WebEngine first (this is crucial for Qt WebEngine to work)
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication
    # Set attribute before QApplication creation
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
except ImportError:
    # Continue anyway to show detailed error information
    pass

def main():
    """Run the Dream.OS PyQt interface with explicit window handling."""
    # Get logger using the factory
    # Note: Log file will be in outputs/logs/run_app.log
    logger = LoggerFactory.create_standard_logger(
        name="fixed_app", 
        level=logging.DEBUG, 
        log_to_file=True
    )

    try:
        # Log Python environment info
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Python executable: {sys.executable}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
        
        # Import and run the application
        logger.info("Importing PyQt components...")
        from PyQt5.QtWidgets import QApplication
        from interfaces.pyqt.DreamOsMainWindow import DreamOsMainWindow
        
        logger.info("Creating application...")
        app = QApplication(sys.argv)
        
        logger.info("Creating main window...")
        window = DreamOsMainWindow()
        
        logger.info("Showing main window...")
        window.show()
        
        logger.info("Entering application main loop...")
        return app.exec_()
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error(f"Import error traceback:\n{traceback.format_exc()}")
        
        # Try to show an error window
        try:
            from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
            
            app = QApplication(sys.argv)
            
            # Create main window
            window = QMainWindow()
            window.setWindowTitle("Dream.OS Error")
            window.setGeometry(100, 100, 800, 600)
            
            # Create central widget and layout
            central_widget = QWidget()
            window.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            
            # Add information about the error
            error_label = QLabel(f"Failed to load the main application: {e}")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)
            
            # Show full traceback
            traceback_label = QLabel(traceback.format_exc())
            traceback_label.setWordWrap(True)
            layout.addWidget(traceback_label)
            
            # Display the window
            window.show()
            logger.info("Error window displayed")
            
            return app.exec_()
        except Exception as fallback_error:
            logger.error(f"Failed to show error window: {fallback_error}")
            return 1
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(f"Error traceback:\n{traceback.format_exc()}")
        # Try to show error window as above
        try:
            from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
            
            app = QApplication(sys.argv)
            
            # Create main window
            window = QMainWindow()
            window.setWindowTitle("Dream.OS Error")
            window.setGeometry(100, 100, 800, 600)
            
            # Create central widget and layout
            central_widget = QWidget()
            window.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            
            # Add information about the error
            error_label = QLabel(f"Unexpected error: {e}")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)
            
            # Show full traceback
            traceback_label = QLabel(traceback.format_exc())
            traceback_label.setWordWrap(True)
            layout.addWidget(traceback_label)
            
            # Display the window
            window.show()
            logger.info("Error window displayed")
            
            return app.exec_()
        except Exception as fallback_error:
            logger.error(f"Failed to show error window: {fallback_error}")
            return 1

if __name__ == '__main__':
    sys.exit(main()) 