"""
Factory for creating Merit Test related instances.
"""
from typing import Optional, Any
from core.services.service_registry import ServiceRegistry

class MeritTestFactory:
    """Factory for creating Merit Test related instances."""
    
    @staticmethod
    def create(registry: ServiceRegistry) -> Optional[Any]:
        """
        Create and return a configured Merit Test instance.
        
        Args:
            registry: The service registry containing dependencies
            
        Returns:
            A fully configured Merit Test instance
        """
        try:
            # Get dependencies
            logger = registry.get("logger")
            config = registry.get("config_manager")
            prompt_manager = registry.get("prompt_manager")
            chat_manager = registry.get("chat_manager")
            
            # Import here to avoid circular dependencies
            from core.merit.merit_chain_manager import MeritChainManager
            from core.merit.test_coverage_analyzer import TestCoverageAnalyzer
            from core.merit.test_generator_service import TestGeneratorService
            
            # Create and return the appropriate instance based on the service name
            service_name = registry.get("service_name")
            if service_name == "merit_chain_manager":
                instance = MeritChainManager(
                    prompt_manager=prompt_manager,
                    chat_manager=chat_manager,
                    config=config,
                    logger=logger
                )
            elif service_name == "test_coverage_analyzer":
                instance = TestCoverageAnalyzer(
                    config=config,
                    logger=logger
                )
            elif service_name == "test_generator_service":
                instance = TestGeneratorService(
                    prompt_manager=prompt_manager,
                    chat_manager=chat_manager,
                    config=config,
                    logger=logger
                )
            else:
                raise ValueError(f"Unknown service name: {service_name}")
            
            if logger:
                logger.info(f"✅ {service_name} created successfully")
                
            return instance
            
        except Exception as e:
            if logger:
                logger.error(f"❌ Failed to create Merit Test instance: {e}")
            return None 