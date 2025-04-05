"""Entry point for the PyQt interface."""
import sys
import logging
from pathlib import Path

# Import Qt WebEngine first - this MUST happen before QApplication is created
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication
    # Set this attribute before QApplication creation
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
except ImportError as e:
    print(f"WARNING: Failed to import Qt WebEngine: {e}")
    print("This may cause problems with web-based components")

# Configure logging
# Define handlers with UTF-8 encoding
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
stdout_handler.encoding = 'utf-8'

file_handler = logging.FileHandler('dream_os_debug.log', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[stdout_handler, file_handler]
)

logger = logging.getLogger(__name__)

def main():
    try:
        from PyQt5.QtWidgets import QApplication
        from interfaces.pyqt import DreamOsMainWindow
        
        app = QApplication(sys.argv)
        window = DreamOsMainWindow()
        
        # Make sure the window is shown
        window.show()
        logger.info("Main window shown")
        
        # This starts the Qt event loop and blocks until the application exits
        logger.info("Starting Qt event loop (app.exec_())")
        return app.exec_()
    except Exception as e:
        logger.exception("Failed to start Dream.OS:")
        return 1

if __name__ == "__main__":
    sys.exit(main())
