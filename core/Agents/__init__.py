# AUTO-GENERATED __init__.py
# DO NOT EDIT MANUALLY - changes may be overwritten

from . import AgentDispatcher
from . import CursorAgentInterface
from . import DocAgent
from . import RefactorAgent
from . import ReinforcementEvaluator
from . import TestAgent
from . import base_agent
from . import chat_scraper_agent
from . import main
from . import refactoring_utils
from . import specialized_agents

__all__ = [
    'AgentDispatcher',
    'CursorAgentInterface',
    'DocAgent',
    'RefactorAgent',
    'ReinforcementEvaluator',
    'TestAgent',
    'base_agent',
    'chat_scraper_agent',
    'main',
    'refactoring_utils',
    'specialized_agents',
]

"""
Core Agents Module

This module provides a standardized framework for all agent implementations
with proper lifecycle management and dependency injection.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum
import logging
from dataclasses import dataclass
from datetime import datetime

class AgentState(Enum):
    """Possible states an agent can be in."""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    TERMINATED = "terminated"

@dataclass
class AgentMetrics:
    """Metrics tracking for agent performance and health."""
    created_at: datetime
    last_active: datetime
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    average_response_time: float = 0.0
    memory_usage: float = 0.0
    error_rate: float = 0.0

class AgentContext:
    """Context object for managing agent state and dependencies."""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("AgentContext")
        self.state = AgentState.INITIALIZING
        self.metrics = AgentMetrics(
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow()
        )
        self._dependencies: Dict[str, Any] = {}
    
    def add_dependency(self, name: str, instance: Any) -> None:
        """Add a dependency to the context."""
        self._dependencies[name] = instance
    
    def get_dependency(self, name: str) -> Optional[Any]:
        """Get a dependency from the context."""
        return self._dependencies.get(name)
    
    def update_state(self, new_state: AgentState) -> None:
        """Update agent state and last active timestamp."""
        self.state = new_state
        self.metrics.last_active = datetime.utcnow()
    
    def record_operation(self, success: bool, response_time: float = 0.0) -> None:
        """Record metrics for an operation."""
        self.metrics.total_operations += 1
        if success:
            self.metrics.successful_operations += 1
        else:
            self.metrics.failed_operations += 1
        
        # Update average response time
        if self.metrics.total_operations > 0:
            current_total = (self.metrics.average_response_time * 
                           (self.metrics.total_operations - 1) + response_time)
            self.metrics.average_response_time = current_total / self.metrics.total_operations
        
        # Update error rate
        self.metrics.error_rate = (self.metrics.failed_operations / 
                                 self.metrics.total_operations if self.metrics.total_operations > 0 else 0.0)

class BaseAgent(ABC):
    """Base class for all agents with lifecycle management."""
    
    def __init__(self, context: AgentContext):
        self.context = context
        self.logger = context.logger
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the agent and its resources."""
        pass
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Execute the agent's main functionality."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources when shutting down."""
        pass
    
    async def pause(self) -> None:
        """Pause agent operations."""
        if self.context.state == AgentState.RUNNING:
            self.context.update_state(AgentState.PAUSED)
            self.logger.info(f"{self.__class__.__name__} paused")
    
    async def resume(self) -> None:
        """Resume agent operations."""
        if self.context.state == AgentState.PAUSED:
            self.context.update_state(AgentState.RUNNING)
            self.logger.info(f"{self.__class__.__name__} resumed")
    
    async def terminate(self) -> None:
        """Terminate the agent."""
        try:
            await self.cleanup()
            self.context.update_state(AgentState.TERMINATED)
            self.logger.info(f"{self.__class__.__name__} terminated")
        except Exception as e:
            self.logger.error(f"Error terminating {self.__class__.__name__}: {e}")
            self.context.update_state(AgentState.ERROR)
    
    def get_metrics(self) -> AgentMetrics:
        """Get current agent metrics."""
        return self.context.metrics
    
    def get_state(self) -> AgentState:
        """Get current agent state."""
        return self.context.state

class AgentLifecycleManager:
    """Manager for handling agent lifecycle and dependencies."""
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self.logger = logging.getLogger("AgentLifecycleManager")
    
    async def create_agent(
        self,
        agent_class: type,
        agent_id: str,
        config: Dict[str, Any],
        dependencies: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseAgent]:
        """Create and initialize a new agent."""
        try:
            # Create context
            context = AgentContext(config, self.logger.getChild(agent_id))
            
            # Add dependencies
            if dependencies:
                for name, instance in dependencies.items():
                    context.add_dependency(name, instance)
            
            # Create and initialize agent
            agent = agent_class(context)
            if await agent.initialize():
                self._agents[agent_id] = agent
                return agent
            
            self.logger.error(f"Failed to initialize agent {agent_id}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error creating agent {agent_id}: {e}")
            return None
    
    async def terminate_agent(self, agent_id: str) -> bool:
        """Terminate and remove an agent."""
        agent = self._agents.get(agent_id)
        if agent:
            await agent.terminate()
            del self._agents[agent_id]
            return True
        return False
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)
    
    def get_all_agents(self) -> List[BaseAgent]:
        """Get all registered agents."""
        return list(self._agents.values())
    
    async def terminate_all(self) -> None:
        """Terminate all agents."""
        for agent_id in list(self._agents.keys()):
            await self.terminate_agent(agent_id)

# Create global lifecycle manager instance
lifecycle_manager = AgentLifecycleManager()
