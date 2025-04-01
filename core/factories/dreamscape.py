"""
Unified Dreamscape Factory

This module provides a centralized factory for creating dreamscape-related services
including DreamscapeGenerationService and its dependencies.
"""

from typing import Optional, Any, Dict
from datetime import datetime
import logging
from core.factories import BaseFactory, FactoryRegistry

class DreamscapeFactory(BaseFactory):
    """Factory for creating dreamscape-related services."""
    
    def create(self) -> Any:
        """Create and return a dreamscape service instance."""
        try:
            # Get dependencies
            deps = self.get_dependencies()
            logger = deps["logger"]
            config = deps["config"]
            path_manager = deps["path_manager"]
            
            # Import here to avoid circular dependencies
            from core.services.dreamscape_generator_service import DreamscapeGenerationService
            from core.services.service_registry import registry
            
            # Get or create required services
            template_manager = registry.get("template_manager")
            if not template_manager:
                from core.TemplateManager import TemplateManager
                template_manager = TemplateManager()
                registry.register("template_manager", instance=template_manager)
            
            # Resolve paths
            output_dir = path_manager.get_output_path() / "dreamscape"
            memory_file = path_manager.get_memory_path() / "dreamscape_memory.json"
            
            # Load or initialize memory
            memory_data = self._load_or_initialize_memory(memory_file)
            
            # Create the service
            service = DreamscapeGenerationService(
                config_service=config,
                path_manager=path_manager,
                template_manager=template_manager,
                logger=logger,
                memory_data=memory_data
            )
            
            logger.info("✅ Dreamscape services created successfully")
            return service
            
        except Exception as e:
            logger.error(f"❌ Failed to create dreamscape services: {e}")
            return None
    
    def _load_or_initialize_memory(self, memory_file: str) -> Dict[str, Any]:
        """Load existing dreamscape memory or create default version."""
        from core.memory.utils import load_memory_file
        
        default_memory = {
            "last_updated": datetime.utcnow().isoformat(),
            "episode_count": 0,
            "themes": [],
            "characters": ["Victor the Architect"],
            "realms": ["The Dreamscape", "The Forge of Automation"],
            "artifacts": [],
            "recent_episodes": [],
            "skill_levels": {
                "System Convergence": 1,
                "Execution Velocity": 1,
                "Memory Integration": 1,
                "Protocol Design": 1,
                "Automation Engineering": 1
            },
            "architect_tier": {
                "current_tier": "Initiate Architect",
                "progress": "0%",
                "tier_history": []
            },
            "quests": {
                "completed": [],
                "active": ["Establish the Dreamscape"]
            },
            "protocols": [],
            "stabilized_domains": []
        }
        
        return load_memory_file(memory_file, default_memory)

# Register the factory
FactoryRegistry.register("dreamscape", DreamscapeFactory) 