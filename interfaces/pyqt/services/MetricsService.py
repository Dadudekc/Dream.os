"""
Metrics Service Module

This module provides a service for tracking and analyzing task execution metrics.
"""

import logging
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MetricsService:
    """Service for tracking and analyzing task execution metrics."""
    
    def __init__(self, metrics_dir: str):
        """
        Initialize the metrics service.
        
        Args:
            metrics_dir: Directory to store metrics data
        """
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.metrics_dir / "task_metrics.json"
        self.metrics_cache: Dict[str, Dict[str, Any]] = {}
        self._load_metrics()
    
    def _load_metrics(self):
        """Load metrics from disk."""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    self.metrics_cache = json.load(f)
                logger.info(f"Loaded metrics from {self.metrics_file}")
        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")
            self.metrics_cache = {}
    
    def _save_metrics(self):
        """Save metrics to disk."""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics_cache, f, indent=2)
            logger.debug("Saved metrics to disk")
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def get_task_metrics(self, task_id: str) -> Dict[str, Any]:
        """
        Get metrics for a specific task.
        
        Args:
            task_id: The task identifier
            
        Returns:
            Dictionary containing task metrics
        """
        return self.metrics_cache.get(task_id, {})
    
    def update_task_metrics(self, task_id: str, status: str, **kwargs):
        """
        Update metrics for a task.
        
        Args:
            task_id: The task identifier
            status: Current task status
            **kwargs: Additional metrics to update
        """
        if task_id not in self.metrics_cache:
            self.metrics_cache[task_id] = {
                "created_at": datetime.now().isoformat(),
                "status_history": [],
                "prompt_count": 0,
                "execution_cycles": 0,
                "retry_count": 0,
                "total_execution_time": 0,
                "success_count": 0,
                "error_count": 0,
                "stall_count": 0,
                "recovery_attempts": 0,
                "successful_recoveries": 0,
                "recovery_actions": {}  # Track success rate of different recovery actions
            }
        
        metrics = self.metrics_cache[task_id]
        current_time = datetime.now()
        
        # Update status history
        metrics["status_history"].append({
            "status": status,
            "timestamp": current_time.isoformat(),
            **kwargs
        })
        
        # Update status-specific metrics
        if status == "queued":
            metrics["execution_cycles"] += 1
        elif status == "completed":
            metrics["success_count"] += 1
            if "result" in kwargs:
                metrics["last_result"] = kwargs["result"]
            if "execution_time" in kwargs:
                metrics["total_execution_time"] += kwargs["execution_time"]
        elif status in ["error", "failed"]:
            metrics["error_count"] += 1
            if "error" in kwargs:
                metrics["last_error"] = kwargs["error"]
        elif status == "recovering":
            metrics["recovery_attempts"] += 1
            if "recovery_action" in kwargs:
                action = kwargs["recovery_action"]
                if action not in metrics["recovery_actions"]:
                    metrics["recovery_actions"][action] = {
                        "attempts": 0,
                        "successes": 0
                    }
                metrics["recovery_actions"][action]["attempts"] += 1
        
        # Track stalls
        if "stall_detected" in kwargs and kwargs["stall_detected"]:
            metrics["stall_count"] += 1
        
        # Track successful recoveries
        if status == "completed" and metrics["recovery_attempts"] > 0:
            metrics["successful_recoveries"] += 1
            if "recovery_action" in kwargs:
                action = kwargs["recovery_action"]
                if action in metrics["recovery_actions"]:
                    metrics["recovery_actions"][action]["successes"] += 1
        
        # Update retry count if provided
        if "retry_count" in kwargs:
            metrics["retry_count"] = kwargs["retry_count"]
        
        # Calculate success rate
        total_attempts = metrics["success_count"] + metrics["error_count"]
        metrics["success_rate"] = (metrics["success_count"] / total_attempts * 100) if total_attempts > 0 else 0
        
        # Calculate recovery success rate
        if metrics["recovery_attempts"] > 0:
            metrics["recovery_success_rate"] = (metrics["successful_recoveries"] / metrics["recovery_attempts"] * 100)
        else:
            metrics["recovery_success_rate"] = 0
        
        # Save updated metrics
        self._save_metrics()
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """
        Get global execution metrics across all tasks.
        
        Returns:
            Dictionary containing global metrics
        """
        total_tasks = len(self.metrics_cache)
        if total_tasks == 0:
            return {
                "total_tasks": 0,
                "success_rate": 0,
                "average_execution_time": 0,
                "total_execution_cycles": 0,
                "total_stalls": 0,
                "recovery_success_rate": 0,
                "recovery_action_stats": {}
            }
        
        total_success = sum(m["success_count"] for m in self.metrics_cache.values())
        total_cycles = sum(m["execution_cycles"] for m in self.metrics_cache.values())
        total_time = sum(m["total_execution_time"] for m in self.metrics_cache.values())
        total_stalls = sum(m["stall_count"] for m in self.metrics_cache.values())
        total_recoveries = sum(m["recovery_attempts"] for m in self.metrics_cache.values())
        successful_recoveries = sum(m["successful_recoveries"] for m in self.metrics_cache.values())
        
        # Aggregate recovery action statistics
        recovery_action_stats = {}
        for metrics in self.metrics_cache.values():
            for action, stats in metrics["recovery_actions"].items():
                if action not in recovery_action_stats:
                    recovery_action_stats[action] = {"attempts": 0, "successes": 0}
                recovery_action_stats[action]["attempts"] += stats["attempts"]
                recovery_action_stats[action]["successes"] += stats["successes"]
        
        return {
            "total_tasks": total_tasks,
            "success_rate": (total_success / total_tasks) * 100,
            "average_execution_time": total_time / total_tasks if total_tasks > 0 else 0,
            "total_execution_cycles": total_cycles,
            "total_stalls": total_stalls,
            "recovery_success_rate": (successful_recoveries / total_recoveries * 100) if total_recoveries > 0 else 0,
            "recovery_action_stats": recovery_action_stats,
            "tasks_by_status": self._get_tasks_by_status(),
            "hourly_execution_stats": self._get_hourly_stats()
        }
    
    def _get_tasks_by_status(self) -> Dict[str, int]:
        """Get count of tasks in each status."""
        status_counts = {}
        for metrics in self.metrics_cache.values():
            if metrics["status_history"]:
                current_status = metrics["status_history"][-1]["status"]
                status_counts[current_status] = status_counts.get(current_status, 0) + 1
        return status_counts
    
    def _get_hourly_stats(self) -> Dict[str, Any]:
        """Get execution statistics by hour for the last 24 hours."""
        now = datetime.now()
        hourly_stats = {
            "executions": [0] * 24,
            "successes": [0] * 24,
            "failures": [0] * 24
        }
        
        for metrics in self.metrics_cache.values():
            for status_entry in metrics["status_history"]:
                try:
                    timestamp = datetime.fromisoformat(status_entry["timestamp"])
                    if now - timestamp <= timedelta(hours=24):
                        hour_index = 23 - (now - timestamp).seconds // 3600
                        if hour_index >= 0:
                            hourly_stats["executions"][hour_index] += 1
                            if status_entry["status"] == "completed":
                                hourly_stats["successes"][hour_index] += 1
                            elif status_entry["status"] in ["error", "failed"]:
                                hourly_stats["failures"][hour_index] += 1
                except (ValueError, KeyError):
                    continue
        
        return hourly_stats 