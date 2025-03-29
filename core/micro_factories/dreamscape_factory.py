"""
Factory for creating DreamscapeGeneratorService instances.
Supports registry-based creation and explicit dependency injection.
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class DreamscapeFactory:
    """Micro-factory for creating DreamscapeGeneratorService instances."""

    @staticmethod
    def create() -> Optional[Any]:
        """
        Create and return a DreamscapeGenerationService using services from the ServiceRegistry.
        """
        try:
            from core.services.service_registry import ServiceRegistry
            from core.services.dreamscape_generator_service import DreamscapeGenerationService
            from core.PathManager import PathManager
            from core.TemplateManager import TemplateManager

            # Get core dependencies from registry
            path_manager = ServiceRegistry.get("path_manager") or PathManager()
            config_manager = ServiceRegistry.get("config_manager")
            logger_agent = ServiceRegistry.get("logger") or logger
            
            # Create template manager
            template_manager = TemplateManager()
            
            # Initialize memory data
            memory_data = {}
            try:
                # Try to get standard memory path
                memory_path = path_manager.get_memory_path() / "dreamscape_memory.json"
                if memory_path.exists():
                    import json
                    with open(memory_path, 'r', encoding='utf-8') as f:
                        memory_data = json.load(f)
                    logger.info(f"Loaded dreamscape memory from {memory_path}")
            except Exception as e:
                logger.warning(f"Could not load dreamscape memory: {e}")

            return DreamscapeGenerationService(
                path_manager=path_manager,
                template_manager=template_manager,
                logger=logger_agent,
                memory_data=memory_data
            )

        except Exception as e:
            logger.error(f"❌ Failed to create DreamscapeGenerationService: {e}")
            return None

    @staticmethod
    def create_with_explicit_deps(
        path_manager: Optional[Any]=None,
        template_manager: Optional[Any]=None,
        memory_data: Optional[Any]=None,
        logger_instance: Optional[Any]=None
    ) -> Optional[Any]:
        """
        Create and return a DreamscapeGenerationService with explicit dependencies.
        """
        try:
            from core.services.dreamscape_generator_service import DreamscapeGenerationService
            from core.PathManager import PathManager
            from core.TemplateManager import TemplateManager
            
            return DreamscapeGenerationService(
                path_manager=path_manager or PathManager(),
                template_manager=template_manager or TemplateManager(),
                logger=logger_instance or logger,
                memory_data=memory_data or {}
            )
        except Exception as e:
            logger.error(f"❌ Failed to create DreamscapeGenerationService with explicit deps: {e}")
            return None
