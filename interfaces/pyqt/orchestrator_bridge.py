#!/usr/bin/env python3
"""
OrchestratorBridge

This module provides a bridge between the PromptCycleOrchestrator's event system
and PyQt5 signals that can be connected to UI components.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, List
from PyQt5.QtCore import QObject, pyqtSignal

# Add parent directory to path to allow importing from modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from core.prompt_cycle_orchestrator import PromptCycleOrchestrator

logger = logging.getLogger(__name__)


class OrchestratorBridge(QObject):
    """
    Bridge between PromptCycleOrchestrator events and Qt signals.
    
    This class provides Qt signals that UI components can connect to, and
    registers event handlers with the orchestrator to emit those signals.
    """
    
    # Define signals
    scan_completed = pyqtSignal(dict)
    task_generated = pyqtSignal(dict)
    task_execution_started = pyqtSignal(dict)
    task_execution_completed = pyqtSignal(dict)
    task_requeued = pyqtSignal(dict)
    tasks_requeued = pyqtSignal(dict)
    cycle_started = pyqtSignal(dict)
    cycle_completed = pyqtSignal(dict)
    context_changed = pyqtSignal(dict)
    
    def __init__(self, orchestrator: PromptCycleOrchestrator):
        """
        Initialize the OrchestratorBridge.
        
        Args:
            orchestrator: The PromptCycleOrchestrator instance to bridge
        """
        super().__init__()
        self.orchestrator = orchestrator
        
        # Register event handlers
        self._register_event_handlers()
        
        logger.info("OrchestratorBridge initialized")
    
    def _register_event_handlers(self):
        """Register event handlers with the orchestrator."""
        # Map orchestrator events to signals
        event_mapping = {
            "scan_complete": self.scan_completed,
            "task_generated": self.task_generated,
            "task_execution_started": self.task_execution_started,
            "task_execution_completed": self.task_execution_completed,
            "task_requeued": self.task_requeued,
            "tasks_requeued": self.tasks_requeued,
            "cycle_started": self.cycle_started,
            "cycle_completed": self.cycle_completed,
            "context_changed": self.context_changed
        }
        
        # Register each event handler
        for event_name, signal in event_mapping.items():
            # Create a lambda that captures the signal variable
            handler = lambda data, signal=signal: signal.emit(data)
            self.orchestrator.register_event_handler(event_name, handler)
            
        logger.debug("Event handlers registered with orchestrator")
    
    def requeue_task(self, task_id: str) -> bool:
        """
        Requeue a task for execution.
        
        Args:
            task_id: ID of the task to requeue
            
        Returns:
            True if requeued successfully, False otherwise
        """
        try:
            # Requeue the task using the execution service
            success = self.orchestrator.execution_service.requeue_task(task_id)
            
            if success:
                logger.info(f"Task {task_id} requeued successfully")
                # Emit a signal to update UI
                self.task_requeued.emit({"task_id": task_id, "success": True})
            else:
                logger.warning(f"Failed to requeue task {task_id}")
                self.task_requeued.emit({"task_id": task_id, "success": False})
            
            return success
        except Exception as e:
            logger.error(f"Error requeuing task {task_id}: {e}")
            self.task_requeued.emit({"task_id": task_id, "success": False, "error": str(e)})
            return False
    
    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """
        Execute a specific task.
        
        Args:
            task_id: ID of the task to execute
            
        Returns:
            Execution result
        """
        results = self.orchestrator.execute_tasks([task_id])
        return results[0] if results else {}
    
    def refresh_tasks(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Refresh and return the current tasks.
        
        Returns:
            Dictionary containing queued and executed tasks
        """
        queued_tasks = self.orchestrator.execution_service.get_queued_tasks()
        executed_tasks = self.orchestrator.execution_service.get_executed_tasks()
        
        return {
            "queued": queued_tasks,
            "executed": executed_tasks
        }
    
    def validate_task(self, task_id: str, criteria: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Validate a specific task using custom or default criteria.
        
        Args:
            task_id: ID of the task to validate
            criteria: Optional validation criteria
            
        Returns:
            Validation result
        """
        # Get the task from executed tasks
        executed_tasks = self.orchestrator.execution_service.get_executed_tasks()
        task = next((t for t in executed_tasks if t.get("id") == task_id), None)
        
        if not task:
            logger.warning(f"Task {task_id} not found in executed tasks")
            return {"passed": False, "error": "Task not found"}
        
        # Use criteria from task if not provided
        if criteria is None and "validation_criteria" in task:
            criteria = task["validation_criteria"]
        elif criteria is None:
            criteria = {"min_length": 100}
        
        # Get the result from the task
        result = task.get("result", {})
        if not result:
            logger.warning(f"Task {task_id} has no result")
            return {"passed": False, "error": "Task has no result"}
        
        # Validate the result
        validation = self.orchestrator.ui_service.validate_task_result(result, criteria)
        return validation 