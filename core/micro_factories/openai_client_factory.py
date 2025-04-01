"""
OpenAI Client Factory Module

This module provides factory methods for creating OpenAI clients
with proper configuration and error handling.
"""

from typing import Any, Dict, Optional
from core.factories import BaseFactory, FactoryRegistry

class OpenAIClientFactory(BaseFactory):
    """Factory for creating OpenAI clients."""
    
    def create(self, service_registry: Any = None, headless: bool = False, **kwargs) -> Any:
        """Create and return an OpenAI client instance."""
        try:
            # Get dependencies
            deps = self.get_dependencies()
            logger = deps["logger"]
            config = deps["config"]
            
            # Get API key from config
            api_key = config.get("openai_api_key")
            if not api_key:
                logger.error("❌ No OpenAI API key found in config")
                return None
                
            # Import OpenAI here to avoid loading it unless needed
            import openai
            
            # Configure client
            openai.api_key = api_key
            
            # Create a simple wrapper class to represent the client
            class OpenAIClient:
                def __init__(self, api_key: str):
                    self.api_key = api_key
                    self.client = openai
                
                def get_client(self):
                    return self.client
            
            client = OpenAIClient(api_key)
            logger.info("✅ OpenAI client created successfully")
            return client
            
        except Exception as e:
            logger.error(f"❌ Failed to create OpenAI client: {e}")
            return None

# Register the factory
FactoryRegistry.register("openai_client", OpenAIClientFactory) 