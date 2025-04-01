"""
Unified Agent Factory

This module provides a centralized factory for creating agent-related services
using the standardized agent framework.
"""

from typing import Optional, Any, Dict, Type
import logging
from core.factories import BaseFactory, FactoryRegistry
from core.agents import AgentContext, AgentState

class AgentFactory(BaseFactory):
    """Factory for creating agent-related services."""
    
    _agent_types: Dict[str, Type] = {}
    
    @classmethod
    def register_agent_type(cls, name: str, agent_class: Type) -> None:
        """Register an agent class type."""
        cls._agent_types[name] = agent_class
    
    def create(self, agent_type: str = "chat") -> Any:
        """Create and return an agent instance."""
        try:
            # Get dependencies
            deps = self.get_dependencies()
            logger = deps["logger"]
            config = deps["config"]
            
            # Import here to avoid circular dependencies
            from core.services.service_registry import registry
            
            # Get agent class
            agent_class = self._agent_types.get(agent_type)
            if not agent_class:
                raise ValueError(f"Unknown agent type: {agent_type}")
            
            # Create agent context
            context = AgentContext(config, logger.getChild(f"{agent_type}_agent"))
            
            # Add dependencies based on agent type
            if agent_type == "chat":
                self._setup_chat_dependencies(context, registry)
            elif agent_type == "engagement":
                self._setup_engagement_dependencies(context, registry)
            
            # Create and initialize agent
            agent = agent_class(context)
            
            logger.info(f"✅ {agent_type} agent created successfully")
            return agent
            
        except Exception as e:
            logger.error(f"❌ Failed to create agent: {e}")
            return None
    
    def _setup_chat_dependencies(self, context: AgentContext, registry: Any) -> None:
        """Set up dependencies for chat agent."""
        # Get or create memory manager
        memory_manager = registry.get("memory_manager")
        if not memory_manager:
            from core.memory import MemoryManager
            memory_manager = MemoryManager()
            registry.register("memory_manager", instance=memory_manager)
        
        # Get or create reinforcement engine
        reinforcement_engine = registry.get("reinforcement_engine")
        if not reinforcement_engine:
            from core.ReinforcementEngine import ReinforcementEngine
            reinforcement_engine = ReinforcementEngine()
            registry.register("reinforcement_engine", instance=reinforcement_engine)
        
        # Add dependencies to context
        context.add_dependency("memory_manager", memory_manager)
        context.add_dependency("reinforcement_engine", reinforcement_engine)
    
    def _setup_engagement_dependencies(self, context: AgentContext, registry: Any) -> None:
        """Set up dependencies for engagement agent."""
        # Get or create required services
        env = registry.get("jinja_env")
        if not env:
            from jinja2 import Environment
            env = Environment()
            registry.register("jinja_env", instance=env)
        
        memory_manager = registry.get("engagement_memory_manager")
        if not memory_manager:
            from core.memory import MemoryManager
            memory_manager = MemoryManager(memory_file="memory/engagement_memory.json")
            registry.register("engagement_memory_manager", instance=memory_manager)
        
        reinforcement_engine = registry.get("reinforcement_engine")
        if not reinforcement_engine:
            from core.ReinforcementEngine import ReinforcementEngine
            reinforcement_engine = ReinforcementEngine()
            registry.register("reinforcement_engine", instance=reinforcement_engine)
        
        task_queue_manager = registry.get("task_queue_manager")
        if not task_queue_manager:
            from social.TaskQueueManager import TaskQueueManager
            task_queue_manager = TaskQueueManager()
            registry.register("task_queue_manager", instance=task_queue_manager)
        
        # Add dependencies to context
        context.add_dependency("jinja_env", env)
        context.add_dependency("engagement_memory_manager", memory_manager)
        context.add_dependency("reinforcement_engine", reinforcement_engine)
        context.add_dependency("task_queue_manager", task_queue_manager)

# Register agent types
from core.agents.chat import ChatAgent
from core.agents.engagement import EngagementAgent

AgentFactory.register_agent_type("chat", ChatAgent)
AgentFactory.register_agent_type("engagement", EngagementAgent)

# Register the factory
FactoryRegistry.register("agent", AgentFactory) 