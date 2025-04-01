"""
Metrics Service Module

This module provides centralized metrics collection and analysis for the application,
focusing on performance tracking, recovery metrics, and success rates.
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

class MetricsService:
    """
    Centralized service for collecting and analyzing application metrics.
    
    This service tracks:
    - Task performance & status history
    - Recovery action success rates
    - Global application health metrics
    - Per-component performance data
    """
    
    def __init__(self, memory_manager=None, logger=None):
        """
        Initialize the metrics service.
        
        Args:
            memory_manager: Optional reference to MemoryManager for persistent storage
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.memory_manager = memory_manager
        
        # Thread safety
        self._lock = threading.Lock()
        
        # In-memory cache of metrics
        self.metrics_cache = {}
        
        # Load metrics from persistent storage if available
        self._load_metrics()
        
        self.logger.info("Metrics service initialized")
        
    def update_task_metrics(self, task_id: str, status: str, **metrics) -> None:
        """
        Update metrics for a specific task.
        
        Args:
            task_id: Unique task identifier
            status: New task status
            **metrics: Additional metrics to track
        """
        with self._lock:
            # Initialize metrics for new tasks
            if task_id not in self.metrics_cache:
                self.metrics_cache[task_id] = {
                    "task_id": task_id,
                    "created_at": datetime.now().isoformat(),
                    "status_history": [],
                    "current_status": "",
                    "retry_count": 0,
                    "recovery_actions": [],
                    "execution_time": 0.0
                }
                
            # Update existing metrics
            task_metrics = self.metrics_cache[task_id]
            
            # Handle recovery-specific metrics
            if "recovery_action" in metrics:
                action = metrics["recovery_action"]
                task_metrics["recovery_actions"].append({
                    "action": action,
                    "timestamp": datetime.now().isoformat(),
                    "success": status not in ["error", "stalled"],
                    "execution_time": metrics.get("execution_time", 0.0)
                })
                
                # Update global recovery action stats
                self._update_recovery_action_stats(action, status)
                
            # Update retry count if provided
            if "retry_count" in metrics:
                task_metrics["retry_count"] = metrics["retry_count"]
                
            # Add execution time if provided
            if "execution_time" in metrics:
                task_metrics["execution_time"] += metrics["execution_time"]
                
            # Add status history entry
            status_entry = {
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "metrics": {k: v for k, v in metrics.items() if k != "recovery_action"}
            }
            task_metrics["status_history"].append(status_entry)
            task_metrics["current_status"] = status
            
            # Update all other metrics
            for key, value in metrics.items():
                if key not in ["recovery_action", "retry_count", "execution_time"]:
                    task_metrics[key] = value
                    
            # Save metrics to persistent storage
            self._save_metrics()
            
    def get_task_metrics(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metrics for a specific task.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            Task metrics or None if not found
        """
        return self.metrics_cache.get(task_id)
        
    def get_global_metrics(self) -> Dict[str, Any]:
        """
        Get global metrics aggregated across all tasks.
        
        Returns:
            Dictionary containing global metrics
        """
        with self._lock:
            # Load recovery action stats from memory
            recovery_action_stats = {}
            if self.memory_manager:
                stored_stats = self.memory_manager.get("recovery_action_stats", segment="system")
                if stored_stats:
                    recovery_action_stats = stored_stats
                    
            # Compute task status counts
            status_counts = {}
            error_counts = {}
            total_execution_time = 0.0
            completed_tasks = 0
            error_tasks = 0
            
            for task_id, metrics in self.metrics_cache.items():
                status = metrics["current_status"]
                status_counts[status] = status_counts.get(status, 0) + 1
                
                if status == "error" and "error" in metrics:
                    error = metrics["error"]
                    error_counts[error] = error_counts.get(error, 0) + 1
                    error_tasks += 1
                    
                if status == "completed":
                    completed_tasks += 1
                    total_execution_time += metrics.get("execution_time", 0.0)
                    
            # Calculate average execution time
            avg_execution_time = 0.0
            if completed_tasks > 0:
                avg_execution_time = total_execution_time / completed_tasks
                
            # Calculate success rate
            total_tasks = len(self.metrics_cache)
            success_rate = 0.0
            if total_tasks > 0:
                success_rate = (completed_tasks / total_tasks) * 100
                
            return {
                "task_count": total_tasks,
                "completed_tasks": completed_tasks,
                "error_tasks": error_tasks,
                "success_rate": success_rate,
                "avg_execution_time": avg_execution_time,
                "status_counts": status_counts,
                "error_counts": error_counts,
                "recovery_action_stats": recovery_action_stats
            }
            
    def reset_metrics(self) -> None:
        """Reset all metrics to initial state."""
        with self._lock:
            self.metrics_cache = {}
            if self.memory_manager:
                self.memory_manager.set("metrics_cache", {}, segment="system")
                self.memory_manager.set("recovery_action_stats", {}, segment="system")
                
            self.logger.info("Metrics have been reset")
            
    def _update_recovery_action_stats(self, action: str, status: str) -> None:
        """
        Update stats for a specific recovery action.
        
        Args:
            action: Recovery action name
            status: Resulting status after action
        """
        if not self.memory_manager:
            return
            
        # Get current stats
        stats = self.memory_manager.get("recovery_action_stats", segment="system") or {}
        
        # Initialize stats for new actions
        if action not in stats:
            stats[action] = {
                "attempts": 0,
                "successes": 0,
                "failures": 0,
                "last_used": None
            }
            
        # Update stats
        stats[action]["attempts"] += 1
        stats[action]["last_used"] = datetime.now().isoformat()
        
        if status in ["completed", "recovered"]:
            stats[action]["successes"] += 1
        elif status in ["error", "stalled"]:
            stats[action]["failures"] += 1
            
        # Save updated stats
        self.memory_manager.set("recovery_action_stats", stats, segment="system")
        
    def _load_metrics(self) -> None:
        """Load metrics from persistent storage."""
        if not self.memory_manager:
            return
            
        # Load task metrics
        stored_metrics = self.memory_manager.get("metrics_cache", segment="system")
        if stored_metrics:
            self.metrics_cache = stored_metrics
            self.logger.info(f"Loaded metrics for {len(self.metrics_cache)} tasks")
            
    def _save_metrics(self) -> None:
        """Save metrics to persistent storage."""
        if not self.memory_manager:
            return
            
        # Save task metrics
        self.memory_manager.set("metrics_cache", self.metrics_cache, segment="system") 