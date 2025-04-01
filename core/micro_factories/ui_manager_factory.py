"""
Factory for creating UIManager instances for DreamscapeGenerationTab.
Using a micro-factory pattern with service registry integration.
"""
import logging
from typing import Optional, Any
from interfaces.pyqt.tabs.dreamscape_generation.UIManager import UIManager

logger = logging.getLogger(__name__)

class UIManagerFactory:
    @staticmethod
    def create_dreamscape_ui_manager(parent_widget, logger, template_manager, output_dir):
        """Creates an instance of the Dreamscape UIManager, passing the parent."""
        try:
            # Ensure essential dependencies are provided
            if not all([parent_widget, logger, template_manager, output_dir]):
                error_msg = "Missing required arguments for UIManager creation (excluding episode_list/dropdown)."
                logger.error(f"❌ {error_msg}")
                return None

            # Attempt to import UIManager here
            from interfaces.pyqt.tabs.dreamscape_generation.UIManager import UIManager

            # Pass only the required args
            ui_manager = UIManager(
                parent_widget=parent_widget,
                logger=logger,
                template_manager=template_manager,
                output_dir=output_dir
            )
            logger.info("✅ Dreamscape UIManager created successfully.")
            return ui_manager
        except ImportError as ie:
             logger.error(f"❌ Failed to import UIManager: {ie}. Check circular dependencies or path issues.")
             return None
        except Exception as e:
            logger.error(f"❌ Failed to create DreamscapeUIManager: {e}", exc_info=True) # Log traceback
            return None

# Example basic test or usage (optional, can be removed or expanded)
# if __name__ == '__main__':
#     # This part would require setting up mock objects for testing
#     logging.basicConfig(level=logging.INFO)
#     mock_parent = object() # Replace with actual or mock QWidget
#     mock_logger = logging.getLogger("test_logger")
#     mock_list = object() # Replace with actual or mock QListWidget
#     mock_tm = object() # Replace with actual or mock TemplateManager
#     mock_output_dir = "/path/to/output"
    
#     factory = UIManagerFactory()
#     manager = factory.create_dreamscape_ui_manager(
#         mock_parent, mock_logger, mock_list, mock_tm, mock_output_dir
#     )
    
#     if manager:
#         print("UIManager created via factory.")
#     else:
#         print("UIManager creation failed.") 
