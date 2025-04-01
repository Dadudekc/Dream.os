"""
Prompt Factory Module

This module provides factory methods for creating and managing prompts
with proper dependency injection and lifecycle management.
"""

import logging
from typing import Any, Dict, Optional, Type
from core.factories import BaseFactory, FactoryRegistry
from core.prompts import BasePrompt

logger = logging.getLogger(__name__)

class PromptFactory(BaseFactory):
    """Factory for creating prompt-related services and components."""
    
    def __init__(self):
        """Initialize the prompt factory."""
        self._prompt_types: Dict[str, Type] = {}
        self.register_prompt_type("default", BasePrompt)
    
    def register_prompt_type(self, name: str, prompt_class: Type) -> None:
        """Register a prompt class type."""
        self._prompt_types[name] = prompt_class
    
    def create(self, registry: Any, prompt_type: str = "default", **kwargs) -> Any:
        """Create and return a prompt instance."""
        try:
            # Get dependencies
            deps = self.get_dependencies(registry)
            config = deps["config"]
            
            # Get prompt class
            prompt_class = self._prompt_types.get(prompt_type)
            if not prompt_class:
                raise ValueError(f"Unknown prompt type: {prompt_type}")
            
            # Create prompt instance with dependencies
            prompt = prompt_class(
                config=config,
                logger=logger.getChild(f"{prompt_type}_prompt"),
                **kwargs
            )
            
            logger.info(f"✅ {prompt_type} prompt created successfully")
            return prompt
            
        except Exception as e:
            logger.error(f"❌ Failed to create prompt: {e}")
            return None
    
    def create_from_template(
        self,
        registry: Any,
        template_name: str,
        context: Dict[str, Any],
        **kwargs
    ) -> Optional[str]:
        """Create a prompt from a template."""
        try:
            # Get template engine
            template_env = registry.get("jinja_env")
            if not template_env:
                from jinja2 import Environment, PackageLoader
                template_env = Environment(
                    loader=PackageLoader("core", "templates")
                )
                registry.register("jinja_env", instance=template_env)
            
            # Load and render template
            template = template_env.get_template(template_name)
            return template.render(**context)
            
        except Exception as e:
            logger.error(f"❌ Failed to create prompt from template: {e}")
            return None

# Register the factory
FactoryRegistry.get_instance().register_factory("prompt", PromptFactory()) 