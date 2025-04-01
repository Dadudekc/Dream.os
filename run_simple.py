"""Simple runner for Dream.OS"""
import sys
import os
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

# Add the project root to PYTHONPATH
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

logger.debug(f"Python version: {sys.version}")
logger.debug(f"Project root: {project_root}")
logger.debug(f"PYTHONPATH: {sys.path}")

try:
    logger.debug("Importing PyQt5...")
    from PyQt5.QtWidgets import QApplication
    logger.debug("PyQt5.QtWidgets imported successfully")
    
    logger.debug("Importing DreamOsMainWindow...")
    from interfaces.pyqt.DreamOsMainWindow import DreamOsMainWindow
    logger.debug("DreamOsMainWindow imported successfully")
    
    logger.debug("Creating QApplication...")
    app = QApplication(sys.argv)
    logger.debug("QApplication created successfully")
    
    logger.debug("Creating main window...")
    window = DreamOsMainWindow(app)
    logger.debug("Main window created successfully")
    
    logger.debug("Showing window...")
    window.show()
    logger.debug("Window shown successfully")
    
    logger.debug("Starting event loop...")
    sys.exit(app.exec_())
except Exception as e:
    logger.exception("Error occurred:")
    sys.exit(1) 