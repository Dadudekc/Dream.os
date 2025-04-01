"""Entry point for the PyQt interface."""
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dream_os_debug.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    try:
        from PyQt5.QtWidgets import QApplication
        from interfaces.pyqt import DreamOsMainWindow
        
        app = QApplication(sys.argv)
        window = DreamOsMainWindow(app)
        window.show()
        return app.exec_()
    except Exception as e:
        logger.exception("Failed to start Dream.OS:")
        return 1

if __name__ == "__main__":
    sys.exit(main())
