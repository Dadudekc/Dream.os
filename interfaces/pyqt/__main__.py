"""Entry point for the PyQt interface."""
import sys
import logging
from pathlib import Path

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
        window.show()
        return app.exec_()
    except Exception as e:
        logger.exception("Failed to start Dream.OS:")
        return 1

if __name__ == "__main__":
    sys.exit(main())
