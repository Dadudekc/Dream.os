"""
Adaptive Recovery Service Module

This module provides a service for optimizing recovery strategies based on historical performance.
"""

import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
import json
from pathlib import Path
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)

class AdaptiveRecoveryService:
    """Service for optimizing recovery strategies based on historical performance."""
    
    def __init__(self, metrics_service, config_path: str = "config/recovery_strategies.json"):
        """
        Initialize the adaptive recovery service.
        
        Args:
            metrics_service: Reference to the metrics service
            config_path: Path to recovery strategies configuration
        """
        self.metrics_service = metrics_service
        self.config_path = Path(config_path)
        self.strategies = self._load_strategies()
        self.learning_rate = 0.1  # Rate at which strategy weights are updated
        self.exploration_rate = 0.2  # Probability of trying suboptimal strategy
        
        # Cache for performance metrics
        self.performance_cache = defaultdict(lambda: {
            "success_rate": 0.0,
            "avg_time": 0.0,
            "weight": 1.0,
            "last_updated": None
        })
        
        # Initialize performance tracking
        self._update_performance_metrics()
    
    def _load_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Load recovery strategies from config file."""
        default_strategies = {
            "start_new_chat": {
                "description": "Start a fresh chat session",
                "weight": 1.0,
                "conditions": ["stalled", "timeout"],
                "dependencies": []
            },
            "reload_context": {
                "description": "Reload project and conversation context",
                "weight": 0.8,
                "conditions": ["context_error", "reference_error"],
                "dependencies": []
            },
            "reset_cursor": {
                "description": "Reset cursor state and UI",
                "weight": 0.6,
                "conditions": ["ui_error", "cursor_error"],
                "dependencies": []
            }
        }
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            else:
                # Save default strategies
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.config_path, 'w') as f:
                    json.dump(default_strategies, f, indent=2)
                return default_strategies
        except Exception as e:
            logger.error(f"Failed to load recovery strategies: {e}")
            return default_strategies
    
    def _save_strategies(self):
        """Save current strategies to config file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.strategies, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save recovery strategies: {e}")
    
    def _update_performance_metrics(self):
        """Update performance metrics for all strategies."""
        metrics = self.metrics_service.get_global_metrics()
        action_stats = metrics.get("recovery_action_stats", {})
        
        for action, stats in action_stats.items():
            if action in self.strategies:
                success_rate = (stats["successes"] / stats["attempts"] * 100) if stats["attempts"] > 0 else 0
                
                # Update performance cache
                self.performance_cache[action].update({
                    "success_rate": success_rate,
                    "avg_time": self._calculate_action_avg_time(action),
                    "last_updated": datetime.now().isoformat()
                })
                
                # Update strategy weight based on performance
                self._update_strategy_weight(action)
    
    def _update_strategy_weight(self, action: str):
        """Update strategy weight based on performance metrics."""
        performance = self.performance_cache[action]
        current_weight = self.strategies[action]["weight"]
        
        # Calculate new weight based on success rate and speed
        success_factor = performance["success_rate"] / 100.0
        time_penalty = min(1.0, 10.0 / (performance["avg_time"] + 1))  # Penalize slow strategies
        
        new_weight = (success_factor * 0.7 + time_penalty * 0.3)  # Weighted combination
        
        # Apply learning rate to smooth updates
        updated_weight = current_weight + self.learning_rate * (new_weight - current_weight)
        self.strategies[action]["weight"] = max(0.1, min(1.0, updated_weight))  # Clamp between 0.1 and 1.0
    
    def _calculate_action_avg_time(self, action: str) -> float:
        """Calculate average execution time for a recovery action."""
        times = []
        
        for task in self.metrics_service.metrics_cache.values():
            action_starts = {}
            
            for status in task["status_history"]:
                if status.get("recovery_action") == action:
                    timestamp = datetime.fromisoformat(status["timestamp"])
                    
                    if status["status"] == "recovering":
                        action_starts[action] = timestamp
                    elif status["status"] in ["completed", "failed"]:
                        if action in action_starts:
                            duration = (timestamp - action_starts[action]).total_seconds()
                            times.append(duration)
                            del action_starts[action]
        
        return sum(times) / len(times) if times else float('inf')
    
    def get_next_recovery_action(self, task_context: Dict[str, Any]) -> str:
        """
        Get the next recovery action to try based on current performance metrics.
        
        Args:
            task_context: Dictionary containing task context and error information
            
        Returns:
            Name of the recovery action to try next
        """
        self._update_performance_metrics()
        
        # Get valid strategies for the current context
        valid_strategies = self._get_valid_strategies(task_context)
        
        if not valid_strategies:
            return "start_new_chat"  # Default fallback
        
        # Decide whether to explore or exploit
        if np.random.random() < self.exploration_rate:
            # Exploration: Choose randomly from valid strategies
            return np.random.choice(list(valid_strategies.keys()))
        else:
            # Exploitation: Choose best performing strategy
            return max(valid_strategies.items(), key=lambda x: x[1]["weight"])[0]
    
    def _get_valid_strategies(self, task_context: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Get strategies valid for the current context."""
        valid_strategies = {}
        error_type = task_context.get("error_type", "unknown")
        
        for name, strategy in self.strategies.items():
            # Check if strategy is applicable to current error
            if error_type in strategy["conditions"]:
                # Check if dependencies are satisfied
                if all(dep in self.strategies for dep in strategy["dependencies"]):
                    valid_strategies[name] = strategy
        
        return valid_strategies
    
    def update_strategy_performance(self, action: str, success: bool, execution_time: float):
        """
        Update performance metrics for a strategy after execution.
        
        Args:
            action: Name of the recovery action
            success: Whether the recovery was successful
            execution_time: Time taken to execute the recovery action
        """
        if action not in self.strategies:
            return
            
        performance = self.performance_cache[action]
        
        # Update running averages
        n = performance.get("attempts", 0) + 1
        performance["attempts"] = n
        performance["success_rate"] = (
            (performance["success_rate"] * (n - 1) + (100 if success else 0)) / n
        )
        performance["avg_time"] = (
            (performance["avg_time"] * (n - 1) + execution_time) / n
        )
        performance["last_updated"] = datetime.now().isoformat()
        
        # Update strategy weights
        self._update_strategy_weight(action)
        self._save_strategies()
    
    def get_strategy_insights(self) -> Dict[str, Any]:
        """
        Get insights about strategy performance.
        
        Returns:
            Dictionary containing strategy performance metrics and recommendations
        """
        insights = {
            "strategies": {},
            "recommendations": [],
            "overall_stats": {
                "total_recoveries": 0,
                "success_rate": 0,
                "avg_recovery_time": 0
            }
        }
        
        total_attempts = 0
        total_successes = 0
        total_time = 0
        
        for action, performance in self.performance_cache.items():
            if action in self.strategies:
                strategy_data = {
                    "success_rate": performance["success_rate"],
                    "avg_time": performance["avg_time"],
                    "weight": self.strategies[action]["weight"],
                    "attempts": performance.get("attempts", 0)
                }
                insights["strategies"][action] = strategy_data
                
                total_attempts += strategy_data["attempts"]
                total_successes += (strategy_data["success_rate"] / 100) * strategy_data["attempts"]
                total_time += strategy_data["avg_time"] * strategy_data["attempts"]
        
        # Calculate overall stats
        if total_attempts > 0:
            insights["overall_stats"].update({
                "total_recoveries": total_attempts,
                "success_rate": (total_successes / total_attempts) * 100,
                "avg_recovery_time": total_time / total_attempts
            })
        
        # Generate recommendations
        insights["recommendations"] = self._generate_recommendations()
        
        return insights
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations for improving recovery strategies."""
        recommendations = []
        
        # Analyze strategy performance
        for action, performance in self.performance_cache.items():
            if action in self.strategies:
                if performance["success_rate"] < 50:
                    recommendations.append(
                        f"Consider reviewing '{action}' strategy - low success rate ({performance['success_rate']:.1f}%)"
                    )
                if performance["avg_time"] > 30:  # More than 30 seconds
                    recommendations.append(
                        f"'{action}' strategy is slow (avg {performance['avg_time']:.1f}s) - consider optimization"
                    )
        
        # Check for unused strategies
        for action, strategy in self.strategies.items():
            if action not in self.performance_cache:
                recommendations.append(f"Strategy '{action}' has never been used - consider removal")
        
        return recommendations 