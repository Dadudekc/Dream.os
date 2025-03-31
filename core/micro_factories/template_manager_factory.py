# core/micro_factories/template_manager_factory.py
import logging
import os
from typing import Optional

# Import necessary components
try:
    from core.TemplateManager import TemplateManager
    from core.PathManager import PathManager # Needed to determine default path
except ImportError as e:
    logging.error(f"Failed to import TemplateManager or PathManager: {e}")
    TemplateManager = None
    PathManager = None

logger = logging.getLogger(__name__)

class TemplateManagerFactory:
    @staticmethod
    def create_template_manager(logger_instance: Optional[logging.Logger] = None,
                                template_dir: Optional[str] = None,
                                path_manager: Optional[PathManager] = None) -> Optional[TemplateManager]:
        """
        Factory method to create an instance of TemplateManager.

        Args:
            logger_instance: Logger instance.
            template_dir: Specific directory for templates. If None, uses default.
            path_manager: PathManager instance to find default template dir.

        Returns:
            An instance of TemplateManager or None if creation fails.
        """
        if TemplateManager is None:
            logger.error("❌ TemplateManager class is not available due to import error.")
            return None

        log = logger_instance or logger # Use provided logger or the factory's logger

        resolved_template_dir = template_dir
        if not resolved_template_dir:
            # Determine default directory using PathManager if available
            if path_manager:
                try:
                    resolved_template_dir = path_manager.get_template_path("dreamscape_templates")
                    log.info(f"Using default dreamscape template path from PathManager: {resolved_template_dir}")
                except Exception as e:
                    log.warning(f"⚠️ Failed to get path from PathManager: {e}. Falling back to relative path.")
                    resolved_template_dir = os.path.join(os.getcwd(), "templates", "dreamscape_templates")
            else:
                resolved_template_dir = os.path.join(os.getcwd(), "templates", "dreamscape_templates")
                log.info(f"Using default relative dreamscape template path: {resolved_template_dir}")

        try:
            instance = TemplateManager(
                template_dir=resolved_template_dir,
                logger=log
            )
            log.info(f"✅ TemplateManager created successfully for directory: {resolved_template_dir}")
            return instance
        except Exception as e:
            log.error(f"❌ Failed to create TemplateManager instance: {e}", exc_info=True)
            return None 