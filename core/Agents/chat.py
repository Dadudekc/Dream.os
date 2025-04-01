"""
Chat Agent Implementation

This module provides the chat agent implementation using the standardized
agent framework with proper lifecycle management.
"""

from typing import Any, Dict, List, Optional
import asyncio
import time
from core.agents import BaseAgent, AgentContext, AgentState

class ChatAgent(BaseAgent):
    """Agent for managing chat interactions with proper lifecycle."""
    
    async def initialize(self) -> bool:
        """Initialize chat agent and its dependencies."""
        try:
            # Get required dependencies
            self.memory_manager = self.context.get_dependency("memory_manager")
            self.reinforcement_engine = self.context.get_dependency("reinforcement_engine")
            
            if not self.memory_manager or not self.reinforcement_engine:
                self.logger.error("Missing required dependencies")
                return False
            
            # Initialize configuration
            self.model = self.context.config.get("default_model", "gpt-4")
            self.tone = self.context.config.get("agent_tone", "Victor")
            self.temperature = self.context.config.get("temperature", 0.7)
            self.max_tokens = self.context.config.get("max_tokens", 400)
            self.provider = self.context.config.get("ai_provider", "openai")
            
            # Initialize state
            self.context.update_state(AgentState.READY)
            self.logger.info("Chat agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize chat agent: {e}")
            return False
    
    async def execute(self, prompt: str, **kwargs) -> Optional[str]:
        """Execute a chat interaction."""
        try:
            if self.context.state != AgentState.READY:
                self.logger.error(f"Cannot execute in state: {self.context.state}")
                return None
            
            self.context.update_state(AgentState.RUNNING)
            start_time = time.time()
            
            try:
                # Record context in memory
                self.memory_manager.add_context(prompt)
                
                # Get response using configured model
                response = await self._get_model_response(prompt, **kwargs)
                
                # Apply reinforcement learning
                response = await self._apply_reinforcement(prompt, response)
                
                # Record successful operation
                duration = time.time() - start_time
                self.context.record_operation(True, duration)
                
                return response
                
            finally:
                self.context.update_state(AgentState.READY)
            
        except Exception as e:
            self.logger.error(f"Error executing chat: {e}")
            self.context.record_operation(False)
            return None
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Save memory state
            if self.memory_manager:
                await self.memory_manager.save()
            
            # Clean up any other resources
            self.logger.info("Chat agent cleaned up successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    async def _get_model_response(self, prompt: str, **kwargs) -> str:
        """Get response from the AI model."""
        # Import here to avoid circular dependencies
        from core.services.service_registry import registry
        
        try:
            openai_client = registry.get("openai_client")
            if not openai_client:
                raise ValueError("OpenAI client not available")
            
            response = await openai_client.complete(
                prompt=prompt,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs
            )
            
            return response.choices[0].text.strip()
            
        except Exception as e:
            self.logger.error(f"Error getting model response: {e}")
            raise
    
    async def _apply_reinforcement(self, prompt: str, response: str) -> str:
        """Apply reinforcement learning to improve response."""
        try:
            improved_response = await self.reinforcement_engine.improve_response(
                prompt=prompt,
                response=response,
                tone=self.tone
            )
            return improved_response or response
            
        except Exception as e:
            self.logger.warning(f"Error applying reinforcement: {e}")
            return response 