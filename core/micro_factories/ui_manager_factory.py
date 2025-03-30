"""
Factory for creating UIManager instances for DreamscapeGenerationTab.
Using a micro-factory pattern with service registry integration.
"""
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

def create(
    parent_widget,
    logger=None,
    episode_list=None,
    template_manager=None,
    output_dir=None
) -> Any:
    """
    Create and return a UIManager instance with the provided dependencies.
    
    Args:
        parent_widget: The parent QWidget containing the UI elements
        logger: Logger instance for debugging
        episode_list: QListWidget used for displaying episodes
        template_manager: TemplateManager instance for handling templates
        output_dir: Directory path where episode files are stored
        
    Returns:
        A UIManager instance
    """
    try:
        # Import here to avoid circular dependencies
        from interfaces.pyqt.tabs.dreamscape_generation.UIManager import UIManager
        
        # Create the instance
        ui_manager = UIManager(
            parent_widget=parent_widget,
            logger=logger,
            episode_list=episode_list,
            template_manager=template_manager,
            output_dir=output_dir
        )
        
        if logger:
            logger.info("✅ UIManager created successfully via factory")
        else:
            print("✅ UIManager created successfully via factory")
            
        return ui_manager
        
    except Exception as e:
        error_msg = f"❌ Failed to create UIManager: {e}"
        if logger:
            logger.error(error_msg)
        else:
            print(error_msg)
        return None 