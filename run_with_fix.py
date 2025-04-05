"""
Script to run the Dream.OS PyQt interface with a specific fix for the TaskStatusTab issue.
"""

import os
import sys
import logging
import traceback
import importlib

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("run_with_fix.log", mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RunWithFix")

def patch_task_status_tab():
    """
    Monkey patch the TaskStatusTab class to fix the parent issue.
    """
    try:
        # Only import when needed
        from interfaces.pyqt.tabs.task_status_tab import TaskStatusTab, TaskStatusTabFactory
        
        # Store the original init and create methods
        original_init = TaskStatusTab.__init__
        original_create = TaskStatusTabFactory.create
        
        # Define a safer init method
        def safe_init(self, parent=None, orchestrator_bridge=None):
            if orchestrator_bridge is not None and not isinstance(parent, type):
                # Original expected parent first, then bridge
                try:
                    # Call the original init with only the parent
                    super(TaskStatusTab, self).__init__(parent)
                    self.orchestrator_bridge = orchestrator_bridge
                    # Continue with your own initialization
                    self.services = getattr(parent, 'services', {})
                    self.task_manager = self.services.get('task_manager')
                except Exception as e:
                    logger.error(f"Error in patched init: {e}")
                    # Super minimal init if everything fails
                    from PyQt5.QtWidgets import QWidget
                    super(TaskStatusTab, self).__init__()
            else:
                # Fall back to original behavior if pattern doesn't match what we expect
                original_init(self, parent, orchestrator_bridge)
        
        # Define a safer create method
        def safe_create(parent=None, orchestrator_bridge=None):
            try:
                if orchestrator_bridge is not None:
                    from interfaces.pyqt.tabs.task_status_tab import TaskStatusTab
                    return TaskStatusTab(parent, orchestrator_bridge)
                else:
                    # Default case
                    return original_create(parent)
            except Exception as e:
                logger.error(f"Error in create: {e}")
                # Return a minimal tab if all else fails
                from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
                widget = QWidget(parent)
                layout = QVBoxLayout(widget)
                layout.addWidget(QLabel("TaskStatusTab could not be initialized"))
                return widget
                
        # Apply the patches
        TaskStatusTab.__init__ = safe_init
        TaskStatusTabFactory.create = staticmethod(safe_create)
        
        logger.info("Successfully patched TaskStatusTab")
        return True
    except Exception as e:
        logger.error(f"Failed to patch TaskStatusTab: {e}")
        traceback.print_exc()
        return False

def main():
    """Run the Dream.OS PyQt interface with fixed TaskStatusTab."""
    try:
        # Log Python environment info
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Python executable: {sys.executable}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
        
        # Apply the patch
        patch_success = patch_task_status_tab()
        logger.info(f"Patch application {'succeeded' if patch_success else 'failed'}")
        
        # Import and run the application (with our patch applied)
        logger.info("Importing LoggerFactory...")
        from core.logging.factories.LoggerFactory import LoggerFactory
        app_logger = LoggerFactory.create_standard_logger(
            name="run_patched_app", 
            level=logging.DEBUG, 
            log_to_file=True
        )
        
        logger.info("Importing PyQt interface...")
        from interfaces.pyqt.__main__ import main as pyqt_main
        
        logger.info("Starting PyQt interface...")
        return pyqt_main()
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error(f"Import error traceback:\n{traceback.format_exc()}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(f"Error traceback:\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == '__main__':
    sys.exit(main()) 