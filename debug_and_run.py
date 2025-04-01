"""
Debug and run script for Dream.OS
"""

import os
import sys
import subprocess
import logging
import site
import traceback
from pathlib import Path

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('debug.log')
        ]
    )
    return logging.getLogger(__name__)

def run_command(cmd, check=True):
    """Run a command and return its output."""
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=True,
            text=True,
            shell=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        logger.error(f"Output: {e.output}")
        if check:
            raise
        return None

def check_environment():
    """Check and log environment information."""
    logger.info("=== Environment Information ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    logger.info(f"Site packages: {site.getsitepackages()}")
    
    # Check if we're in a virtual environment
    in_venv = sys.prefix != sys.base_prefix
    logger.info(f"In virtual environment: {in_venv}")
    
    if not in_venv:
        logger.warning("Not running in a virtual environment!")
        venv_path = Path("venv")
        if venv_path.exists():
            logger.info("Found virtual environment directory, attempting to activate...")
            if sys.platform == "win32":
                activate_script = venv_path / "Scripts" / "activate.bat"
                if activate_script.exists():
                    run_command(f"call {activate_script}")
                    logger.info("Virtual environment activated")
            else:
                activate_script = venv_path / "bin" / "activate"
                if activate_script.exists():
                    run_command(f"source {activate_script}")
                    logger.info("Virtual environment activated")

def check_dependencies():
    """Check and install required dependencies."""
    logger.info("=== Checking Dependencies ===")
    
    try:
        import PyQt5
        logger.info(f"PyQt5 version: {PyQt5.QtCore.QT_VERSION_STR}")
    except ImportError:
        logger.warning("PyQt5 not found, installing...")
        run_command("pip install PyQt5")
        
    # Check if our package is installed
    try:
        run_command("pip install -e .")
        logger.info("Package installed in development mode")
    except Exception as e:
        logger.error(f"Failed to install package: {e}")

def main():
    """Main entry point."""
    try:
        check_environment()
        check_dependencies()
        
        logger.info("=== Starting Dream.OS ===")
        from interfaces.pyqt.__main__ import main as pyqt_main
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
    logger = setup_logging()
    main() 