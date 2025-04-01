"""
Agent Failure Hook System

This module provides a unified interface for agents to register failure hooks
and trigger recovery actions through the RecoveryEngine.
"""

import logging
import threading
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class AgentFailureHook:
    """
    Bridge between agents and the recovery engine that allows agents to:
    - Register failure handlers
    - Trigger recovery actions
    - Log failure patterns
    - Update recovery metrics
    """
    
    def __init__(
        self,
        recovery_engine: Any,
        metrics_service: Any,
        memory_manager: Any,
        config_path: str = "config/failure_hooks.json"
    ):
        """
        Initialize the agent failure hook system.
        
        Args:
            recovery_engine: Reference to the RecoveryEngine
            metrics_service: Reference to the MetricsService
            memory_manager: Reference to the MemoryManager
            config_path: Path to failure hooks configuration
        """
        self.recovery_engine = recovery_engine
        self.metrics_service = metrics_service
        self.memory_manager = memory_manager
        self.config_path = Path(config_path)
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Registered failure handlers
        self.failure_handlers: Dict[str, List[Callable]] = {}
        
        # Failure patterns memory
        self.failure_patterns = {}
        
        logger.info("Agent failure hook system initialized")
        
    def register_handler(
        self,
        agent_name: str,
        handler: Callable[[str, Dict[str, Any]], bool],
        error_types: Optional[List[str]] = None
    ) -> None:
        """
        Register a failure handler for an agent.
        
        Args:
            agent_name: Name of the agent registering the handler
            handler: Callback function to handle failures
            error_types: Optional list of error types this handler can process
        """
        with self._lock:
            if agent_name not in self.failure_handlers:
                self.failure_handlers[agent_name] = []
            
            handler_info = {
                "handler": handler,
                "error_types": error_types or ["*"],
                "registered_at": datetime.now().isoformat()
            }
            
            self.failure_handlers[agent_name].append(handler_info)
            logger.info(f"Registered failure handler for {agent_name}")
            
    def handle_failure(
        self,
        agent_name: str,
        error_type: str,
        error_context: Dict[str, Any]
    ) -> bool:
        """
        Handle an agent failure by:
        1. Logging the failure
        2. Updating failure patterns
        3. Triggering appropriate recovery actions
        4. Updating metrics
        
        Args:
            agent_name: Name of the failing agent
            error_type: Type of error encountered
            error_context: Dictionary containing error context and metrics
            
        Returns:
            bool: True if recovery was successful, False otherwise
        """
        logger.warning(f"Handling failure for {agent_name}: {error_type}")
        
        try:
            # Update failure patterns
            self._update_failure_patterns(agent_name, error_type, error_context)
            
            # Find matching handlers
            handlers = self._get_matching_handlers(agent_name, error_type)
            
            if not handlers:
                logger.warning(f"No handlers found for {agent_name} - {error_type}")
                return self._fallback_recovery(agent_name, error_type, error_context)
            
            # Try each handler in sequence
            for handler in handlers:
                try:
                    if handler["handler"](error_type, error_context):
                        self._log_successful_recovery(agent_name, error_type, handler)
                        return True
                except Exception as e:
                    logger.error(f"Handler failed for {agent_name}: {e}")
                    continue
            
            # If all handlers fail, try fallback recovery
            return self._fallback_recovery(agent_name, error_type, error_context)
            
        except Exception as e:
            logger.error(f"Failed to handle failure for {agent_name}: {e}")
            return False
            
    def _update_failure_patterns(
        self,
        agent_name: str,
        error_type: str,
        context: Dict[str, Any]
    ) -> None:
        """Update failure patterns memory."""
        with self._lock:
            if agent_name not in self.failure_patterns:
                self.failure_patterns[agent_name] = {
                    "total_failures": 0,
                    "error_types": {},
                    "recent_failures": []
                }
            
            patterns = self.failure_patterns[agent_name]
            patterns["total_failures"] += 1
            patterns["error_types"].setdefault(error_type, 0)
            patterns["error_types"][error_type] += 1
            
            # Keep last 10 failures for pattern analysis
            failure_entry = {
                "timestamp": datetime.now().isoformat(),
                "error_type": error_type,
                "context": context
            }
            patterns["recent_failures"].append(failure_entry)
            if len(patterns["recent_failures"]) > 10:
                patterns["recent_failures"].pop(0)
            
            # Store patterns in memory manager
            self.memory_manager.set(
                f"failure_patterns_{agent_name}",
                patterns,
                segment="system"
            )
            
    def _get_matching_handlers(
        self,
        agent_name: str,
        error_type: str
    ) -> List[Dict[str, Any]]:
        """Get handlers that can process this error type."""
        matching_handlers = []
        
        if agent_name in self.failure_handlers:
            for handler in self.failure_handlers[agent_name]:
                if "*" in handler["error_types"] or error_type in handler["error_types"]:
                    matching_handlers.append(handler)
                    
        return matching_handlers
        
    def _fallback_recovery(
        self,
        agent_name: str,
        error_type: str,
        context: Dict[str, Any]
    ) -> bool:
        """Attempt fallback recovery using RecoveryEngine."""
        try:
            # Prepare recovery context
            recovery_context = {
                "task_id": context.get("task_id", f"{agent_name}_{datetime.now().timestamp()}"),
                "agent_name": agent_name,
                "error_type": error_type,
                "context": context,
                "metrics": {
                    "retry_count": context.get("retry_count", 0)
                }
            }
            
            # Let RecoveryEngine handle it
            return self.recovery_engine.handle_stall(recovery_context)
            
        except Exception as e:
            logger.error(f"Fallback recovery failed for {agent_name}: {e}")
            return False
            
    def _log_successful_recovery(
        self,
        agent_name: str,
        error_type: str,
        handler: Dict[str, Any]
    ) -> None:
        """Log successful recovery for metrics tracking."""
        try:
            self.metrics_service.update_task_metrics(
                task_id=f"{agent_name}_{datetime.now().timestamp()}",
                status="recovered",
                agent_name=agent_name,
                error_type=error_type,
                recovery_method="handler",
                handler_info={
                    "registered_at": handler["registered_at"],
                    "error_types": handler["error_types"]
                }
            )
        except Exception as e:
            logger.error(f"Failed to log successful recovery: {e}") 