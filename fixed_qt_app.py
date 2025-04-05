"""
Script to run the Dream.OS PyQt interface with comprehensive fixes.
1. Adds Qt WebEngine initialization before creating QApplication
2. Fixes the TaskStatusTab parent/services issue
"""

import os
import sys
import logging
import traceback
import importlib
from PyQt5.QtCore import QSize, QTimer
from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout

# Import QtWebEngine first (this is crucial for Qt WebEngine to work)
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication
    # Set attribute before QApplication creation
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
except ImportError:
    # Continue anyway to show detailed error information
    pass

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fixed_qt_app.log", mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FixedQtApp")

# Initialize Qt WebEngine before importing other PyQt modules
# This is important to prevent crashes on some systems
try:
    import PyQt5.QtWebEngineWidgets
    logger.info("Qt WebEngine initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Qt WebEngine: {e}")

def log_environment_info():
    """Log information about the Python environment for debugging purposes."""
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")

def initialize_webengine():
    """Ensure WebEngine is initialized before creating QApplication.
    
    This is already done at the module level import, but we include this
    function for clarity in the main function.
    """
    # WebEngine is already initialized at the top of the module
    # This function is kept for code clarity in the main() function
    logger.info("WebEngine initialization confirmed")

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
            if orchestrator_bridge is not None and not hasattr(orchestrator_bridge, 'setWindowTitle'):
                # Original expected parent first, then bridge
                try:
                    # Call the original init with only the parent
                    from PyQt5.QtWidgets import QWidget
                    QWidget.__init__(self, parent)
                    self.orchestrator_bridge = orchestrator_bridge
                    # Continue with your own initialization
                    if hasattr(parent, 'services'):
                        self.services = parent.services
                    else:
                        # Create a mock services dict
                        self.services = {}
                    # Handle services.get access pattern
                    if 'task_manager' in self.services:
                        self.task_manager = self.services['task_manager']
                    else:
                        self.task_manager = None
                except Exception as e:
                    logger.error(f"Error in patched init: {e}")
                    # Super minimal init if everything fails
                    from PyQt5.QtWidgets import QWidget
                    QWidget.__init__(self)
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

def patch_draggable_prompt_board_tab():
    """Patch the DraggablePromptBoardTab to handle missing methods."""
    try:
        from interfaces.pyqt.tabs.draggable_prompt_board_tab import DraggablePromptBoardTab
        
        logger.info("Patching DraggablePromptBoardTab...")
        
        # Add the filter_prompts method if it doesn't exist
        if not hasattr(DraggablePromptBoardTab, 'filter_prompts'):
            def filter_prompts(self, search_text):
                """Filter the displayed prompts based on search text."""
                logger.info(f"Filtering prompts with query: {search_text}")
                # If we have no blocks to filter, just return
                if not hasattr(self, 'prompt_board') or not hasattr(self.prompt_board, 'blocks') or not self.prompt_board.blocks:
                    return
                
                search_text = search_text.lower()
                
                # Show all blocks if search text is empty
                if not search_text:
                    for block in self.prompt_board.blocks:
                        block.setVisible(True)
                    return
                    
                # Otherwise, filter based on title, content, or category
                for block in self.prompt_board.blocks:
                    block_data = block.block_data
                    title = block_data.get('title', '').lower()
                    content = block_data.get('content', '').lower()
                    category = block_data.get('category', '').lower()
                    
                    # Show block if any field contains the search text
                    visible = (
                        search_text in title or 
                        search_text in content or 
                        search_text in category
                    )
                    block.setVisible(visible)
            
            # Add the method to the class
            DraggablePromptBoardTab.filter_prompts = filter_prompts
            logger.info("Added filter_prompts method to DraggablePromptBoardTab")
        
        # Add the refresh_board method if it doesn't exist
        if not hasattr(DraggablePromptBoardTab, 'refresh_board'):
            def refresh_board(self):
                """Refresh the board with the latest prompt data."""
                logger.info("Refreshing prompt board")
                # This is a minimal implementation for compatability
                if hasattr(self, 'search_box'):
                    self.search_box.clear()
                # Additional refresh logic would go here
            
            # Add the method to the class
            DraggablePromptBoardTab.refresh_board = refresh_board
            logger.info("Added refresh_board method to DraggablePromptBoardTab")
        
        # Add initialize_data method if it doesn't exist
        if not hasattr(DraggablePromptBoardTab, 'initialize_data'):
            def initialize_data(self):
                """Initialize the board data."""
                logger.info("Initializing prompt board data")
                # This is a minimal implementation for compatability
                if hasattr(self, 'refresh_board'):
                    self.refresh_board()
            
            # Add the method to the class
            DraggablePromptBoardTab.initialize_data = initialize_data
            logger.info("Added initialize_data method to DraggablePromptBoardTab")
        
        logger.info("DraggablePromptBoardTab patched successfully")
    except Exception as e:
        logger.error(f"Error patching DraggablePromptBoardTab: {e}")
        logger.error(traceback.format_exc())

def main():
    """Run the Dream.OS PyQt interface with patches applied."""
    try:
        # Log environment info for debugging
        log_environment_info()
        
        # 1. Initialize PyQt5 WebEngine before creating QApplication
        initialize_webengine()
        
        # 2. Import necessary components - do this after WebEngine init
        from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
        
        # 3. Apply patches to problematic classes
        patch_task_status_tab()
        patch_draggable_prompt_board_tab()
        
        # 4. Create the application and run it
        app = QApplication(sys.argv)
        
        # Import our main window after fixing potential issues
        logger.info("Importing DreamOsMainWindow...")
        from interfaces.pyqt.DreamOsMainWindow import DreamOsMainWindow
        
        # Create and show the main window
        logger.info("Creating and showing main window...")
        window = DreamOsMainWindow()
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
        # Try to show error window similar to above
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