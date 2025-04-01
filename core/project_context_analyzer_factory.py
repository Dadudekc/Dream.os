import logging
from typing import Dict, Any, Optional

from core.project_context_analyzer import ProjectContextAnalyzer
from core.PromptExecutionService import PromptExecutionService

logger = logging.getLogger(__name__)

class ProjectContextAnalyzerFactory:
    """
    Factory for creating ProjectContextAnalyzer instances with validated dependencies.
    Follows the factory pattern to ensure proper initialization.
    """
    
    @staticmethod
    def create(services: Dict[str, Any]) -> Optional[ProjectContextAnalyzer]:
        """
        Create and initialize a ProjectContextAnalyzer with proper dependencies.
        
        Args:
            services: Dictionary containing service instances
            
        Returns:
            Initialized ProjectContextAnalyzer, or None if creation fails
        """
        # Get the prompt service if available
        prompt_service = services.get("prompt_service")
        if prompt_service and not isinstance(prompt_service, PromptExecutionService):
            logger.warning("PromptExecutionService has incorrect type, will not be used for context analysis")
            prompt_service = None
            
        # Create the analyzer
        try:
            analyzer = ProjectContextAnalyzer(
                project_root=".",  # Use current directory
                prompt_service=prompt_service
            )
            
            logger.info("ProjectContextAnalyzer created successfully")
            return analyzer
            
        except Exception as e:
            logger.error(f"Failed to create ProjectContextAnalyzer: {e}")
            return None 