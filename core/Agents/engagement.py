"""
Engagement Agent Implementation

This module provides the engagement agent implementation using the standardized
agent framework with proper lifecycle management.
"""

from typing import Any, Dict, List, Optional
import asyncio
import time
from core.agents import BaseAgent, AgentContext, AgentState

class EngagementAgent(BaseAgent):
    """Agent for managing social engagement with proper lifecycle."""
    
    async def initialize(self) -> bool:
        """Initialize engagement agent and its dependencies."""
        try:
            # Get required dependencies
            self.memory_manager = self.context.get_dependency("engagement_memory_manager")
            self.reinforcement_engine = self.context.get_dependency("reinforcement_engine")
            self.task_queue_manager = self.context.get_dependency("task_queue_manager")
            self.template_env = self.context.get_dependency("jinja_env")
            
            if not all([
                self.memory_manager,
                self.reinforcement_engine,
                self.task_queue_manager,
                self.template_env
            ]):
                self.logger.error("Missing required dependencies")
                return False
            
            # Initialize configuration
            self.platform_strategies = self.context.config.get("platform_strategies", {})
            self.model = self.context.config.get("default_model", "gpt-4")
            self.tone = self.context.config.get("agent_tone", "Victor")
            self.temperature = self.context.config.get("temperature", 0.7)
            self.max_tokens = self.context.config.get("max_tokens", 400)
            self.provider = self.context.config.get("ai_provider", "openai")
            
            # Initialize state
            self.context.update_state(AgentState.READY)
            self.logger.info("Engagement agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize engagement agent: {e}")
            return False
    
    async def execute(self, task_type: str, context: Dict[str, Any], **kwargs) -> Optional[Dict[str, Any]]:
        """Execute an engagement task."""
        try:
            if self.context.state != AgentState.READY:
                self.logger.error(f"Cannot execute in state: {self.context.state}")
                return None
            
            self.context.update_state(AgentState.RUNNING)
            start_time = time.time()
            
            try:
                # Get strategy for task type
                strategy = self.platform_strategies.get(task_type)
                if not strategy:
                    raise ValueError(f"No strategy found for task type: {task_type}")
                
                # Record task context in memory
                self.memory_manager.add_task_context(task_type, context)
                
                # Generate response using template
                template = self.template_env.get_template(strategy["template"])
                prompt = template.render(**context)
                
                # Get model response
                response = await self._get_model_response(prompt, **kwargs)
                
                # Apply reinforcement learning
                response = await self._apply_reinforcement(prompt, response)
                
                # Process response according to strategy
                result = await self._process_response(response, strategy, context)
                
                # Record successful operation
                duration = time.time() - start_time
                self.context.record_operation(True, duration)
                
                return result
                
            finally:
                self.context.update_state(AgentState.READY)
            
        except Exception as e:
            self.logger.error(f"Error executing engagement task: {e}")
            self.context.record_operation(False)
            return None
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Save memory state
            if self.memory_manager:
                await self.memory_manager.save()
            
            # Clean up task queue
            if self.task_queue_manager:
                await self.task_queue_manager.cleanup()
            
            self.logger.info("Engagement agent cleaned up successfully")
            
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
    
    async def _process_response(
        self,
        response: str,
        strategy: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process the response according to the strategy."""
        try:
            processor = strategy.get("processor")
            if processor and callable(processor):
                return await processor(response, context)
            
            # Default processing
            return {
                "raw_response": response,
                "processed": True,
                "context": context,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing response: {e}")
            return {
                "raw_response": response,
                "processed": False,
                "error": str(e),
                "context": context,
                "timestamp": time.time()
            } 