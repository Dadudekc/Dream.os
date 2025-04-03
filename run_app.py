"""
Script to run the Dream.OS PyQt interface with detailed error reporting.
"""

import os
import sys
import logging
import traceback

def setup_logging():
    """Set up logging configuration."""
    # Define handlers with UTF-8 encoding
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    stdout_handler.encoding = 'utf-8' # Specify UTF-8 for stdout

    file_handler = logging.FileHandler('dream_os.log', encoding='utf-8') # Specify UTF-8 for file
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[stdout_handler, file_handler]
    )
    return logging.getLogger(__name__)

def main():
    """Run the Dream.OS PyQt interface."""
    logger = setup_logging()
    
    try:
        # Log Python environment info
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Python executable: {sys.executable}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
        
        # Import and run the application
        logger.info("Importing PyQt interface...")
        from interfaces.pyqt.__main__ import main as pyqt_main
        
        logger.info("Starting PyQt interface...")
        pyqt_main()
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error(f"Import error traceback:\n{traceback.format_exc()}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(f"Error traceback:\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == '__main__':
    main() 