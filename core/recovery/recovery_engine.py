"""
recovery_engine.py - Advanced recovery system for handling task failures

This module provides:
- Adaptive recovery strategies based on error types
- Performance tracking for strategies
- Self-tuning of strategy weights based on success rates
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from pathlib import Path
import random

logger = logging.getLogger(__name__)

class RecoveryEngine:
    """
    Centralized engine for handling task recovery and stall detection.
    
    This class encapsulates all recovery logic, making it reusable across different
    parts of the application. It handles:
    - Stall detection and recovery
    - Recovery strategy selection and optimization
    - Metrics tracking and analysis
    - Recovery action execution
    """
    
    def __init__(
        self,
        cursor_session: Any,
        metrics_service: Any,
        config_path: str = "config/recovery_strategies.json",
        learning_rate: float = 0.1,
        exploration_rate: float = 0.2
    ):
        """
        Initialize the recovery engine.
        
        Args:
            cursor_session: Reference to the CursorSessionManager
            metrics_service: Reference to the MetricsService
            config_path: Path to recovery strategies configuration
            learning_rate: Rate at which strategy weights are updated (0-1)
            exploration_rate: Probability of trying suboptimal strategy (0-1)
        """
        self.cursor_session = cursor_session
        self.metrics_service = metrics_service
        self.config_path = Path(config_path)
        self.learning_rate = learning_rate
        self.exploration_rate = exploration_rate
        
        # Error categories for better recovery targeting
        self.error_categories = {
            "timeout": ["timeout", "timed out", "deadline exceeded"],
            "connection": ["connection", "network", "unreachable"],
            "auth": ["authentication", "unauthorized", "permission"],
            "resource": ["resource", "memory", "disk", "quota"],
            "rate_limit": ["rate limit", "too many requests", "throttle"],
            "context": ["context", "token", "too long"],
            "parsing": ["parse", "syntax", "format", "json"],
            "api": ["api", "endpoint", "service"],
            "ui": ["ui", "interface", "display", "render"],
            "internal": ["internal", "unknown", "unexpected"]
        }
        
        # Load recovery strategies
        self.strategies = self._load_strategies()
        
        # Initialize performance tracking
        self.performance_cache = {}
        self._update_performance_metrics()
        
        logger.info("Recovery engine initialized with %d strategies", len(self.strategies))
    
    def handle_stall(self, task_context: Dict[str, Any]) -> bool:
        """
        Handle a stalled task with adaptive recovery.
        
        Args:
            task_context: Dictionary containing task context and metrics
            
        Returns:
            bool: True if recovery was successful, False otherwise
        """
        task_id = task_context["task_id"]
        retry_count = task_context["metrics"].get("retry_count", 0)
        
        logger.warning(f"Stall detected for task {task_id} (retry {retry_count})")
        
        if retry_count >= task_context["max_retries"]:
            self._handle_max_retries_exceeded(task_id, retry_count)
            return False
            
        try:
            # Select next recovery action
            recovery_action = self._select_recovery_action(task_context)
            logger.info(f"Selected recovery action: {recovery_action}")
            
            # Execute recovery
            success = self.execute_recovery_action(recovery_action, task_context)
            
            # Update metrics and performance data
            self._update_recovery_metrics(task_id, recovery_action, success)
            
            return success
            
        except Exception as e:
            logger.error(f"Recovery failed for task {task_id}: {e}")
            self._update_recovery_metrics(task_id, "unknown", False, error=str(e))
            return False
    
    def execute_recovery_action(self, action: str, task_context: Dict[str, Any]) -> bool:
        """
        Execute a specific recovery action.
        
        Args:
            action: Name of the recovery action to execute
            task_context: Dictionary containing task context
            
        Returns:
            bool: True if action was successful, False otherwise
        """
        if not self.cursor_session:
            logger.error("No cursor session available")
            return False
            
        start_time = time.time()
        task_id = task_context["task_id"]
        
        try:
            if action == "start_new_chat":
                self.cursor_session.start_new_chat()
            else:
                self.cursor_session.execute_recovery_action(action, task_context)
            
            execution_time = time.time() - start_time
            
            # Update task metrics
            self._update_task_metrics(
                task_id,
                "recovering",
                retry_count=task_context["metrics"]["retry_count"] + 1,
                recovery_action=action,
                execution_time=execution_time
            )
            
            # Update strategy performance
            self._update_strategy_performance(action, True, execution_time)
            
            return True
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Recovery action '{action}' failed: {e}")
            
            # Update metrics for failed recovery
            self._update_task_metrics(
                task_id,
                "error",
                error=str(e),
                recovery_action=action,
                execution_time=execution_time
            )
            
            # Update strategy performance
            self._update_strategy_performance(action, False, execution_time)
            
            return False
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive recovery statistics.
        
        Returns:
            Dictionary containing recovery statistics and insights
        """
        stats = {
            "global_metrics": self.metrics_service.get_global_metrics(),
            "strategy_performance": self._get_strategy_performance(),
            "active_recoveries": self._get_active_recoveries(),
            "recommendations": self._generate_recommendations()
        }
        
        return stats
    
    def _load_strategies(self) -> Dict[str, Any]:
        """Load recovery strategies from the config file."""
        default_strategies = {
            "start_new_chat": {
                "weight": 0.7,
                "conditions": ["retry_count > 2", "error_type == 'context'"],
                "success_rate": 0.0,
                "attempts": 0,
                "successes": 0
            },
            "reload_context": {
                "weight": 0.8,
                "conditions": ["error_type == 'parsing'", "retry_count < 3"],
                "success_rate": 0.0,
                "attempts": 0,
                "successes": 0
            },
            "reset_cursor": {
                "weight": 0.6,
                "conditions": ["error_type == 'ui'", "retry_count < 2"],
                "success_rate": 0.0,
                "attempts": 0,
                "successes": 0
            },
            "retry_last_command": {
                "weight": 0.5,
                "conditions": ["error_type == 'timeout'", "error_type == 'connection'"],
                "success_rate": 0.0,
                "attempts": 0,
                "successes": 0
            }
        }
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    loaded_strategies = json.load(f)
                logger.info(f"Loaded {len(loaded_strategies)} strategies from {self.config_path}")
                return loaded_strategies
        except Exception as e:
            logger.error(f"Failed to load strategies from {self.config_path}: {e}")
        
        # Use default strategies if file doesn't exist or has error
        logger.warning(f"Using default recovery strategies")
        return default_strategies
    
    def _select_recovery_action(self, task_context: Dict[str, Any]) -> str:
        """Select the next recovery action based on performance history."""
        self._update_performance_metrics()
        
        # Get valid strategies for the current context
        valid_strategies = self._get_valid_strategies(task_context)
        
        if not valid_strategies:
            return "start_new_chat"  # Default fallback
        
        # Decide whether to explore or exploit
        if random.random() < self.exploration_rate:
            # Exploration: Choose randomly from valid strategies
            return random.choice(list(valid_strategies.keys()))
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
    
    def _update_performance_metrics(self):
        """Update performance metrics for all strategies."""
        metrics = self.metrics_service.get_global_metrics()
        action_stats = metrics.get("recovery_action_stats", {})
        
        for action, stats in action_stats.items():
            if action in self.strategies:
                success_rate = (stats["successes"] / stats["attempts"] * 100) if stats["attempts"] > 0 else 0
                
                self.performance_cache[action] = {
                    "success_rate": success_rate,
                    "avg_time": self._calculate_avg_time(action),
                    "last_updated": datetime.now().isoformat()
                }
                
                self._update_strategy_weight(action)
    
    def _update_strategy_weight(self, action: str):
        """Update strategy weight based on performance metrics."""
        if action not in self.performance_cache:
            return
            
        performance = self.performance_cache[action]
        current_weight = self.strategies[action]["weight"]
        
        # Calculate new weight based on success rate and speed
        success_factor = performance["success_rate"] / 100.0
        time_penalty = min(1.0, 10.0 / (performance["avg_time"] + 1))  # Penalize slow strategies
        
        new_weight = (success_factor * 0.7 + time_penalty * 0.3)  # Weighted combination
        
        # Apply learning rate to smooth updates
        updated_weight = current_weight + self.learning_rate * (new_weight - current_weight)
        self.strategies[action]["weight"] = max(0.1, min(1.0, updated_weight))  # Clamp between 0.1 and 1.0
    
    def _calculate_avg_time(self, action: str) -> float:
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
    
    def _update_task_metrics(
        self,
        task_id: str,
        status: str,
        **metrics
    ) -> None:
        """
        Update task metrics.
        
        Args:
            task_id: Task identifier
            status: New task status
            **metrics: Additional metrics to record
        """
        try:
            if not self.metrics_service:
                logger.warning("No metrics service available")
                return
                
            # Calculate execution time if provided
            if "execution_time" in metrics:
                metrics["execution_time"] = round(metrics["execution_time"], 2)
                
            # If error is present, log failure trace to memory
            if "error" in metrics and status == "error":
                self._log_failure_trace(task_id, metrics)
                
            # Update the metrics and status
            self.metrics_service.update_task_metrics(
                task_id=task_id,
                status=status,
                **metrics
            )
        except Exception as e:
            logger.error(f"Failed to update task metrics: {e}")
            
    def _log_failure_trace(self, task_id: str, metrics: Dict[str, Any]) -> None:
        """
        Log failure trace to memory for long-term pattern recognition.
        
        Args:
            task_id: Task identifier
            metrics: Metrics containing error and context
        """
        try:
            # Skip if we don't have memory access
            if not hasattr(self.metrics_service, "memory_manager"):
                return
                
            memory_manager = self.metrics_service.memory_manager
            if not memory_manager:
                return
                
            # Create failure trace
            failure_trace = {
                "task_id": task_id,
                "timestamp": datetime.now().isoformat(),
                "error": metrics.get("error", "Unknown error"),
                "recovery_action": metrics.get("recovery_action"),
                "retry_count": metrics.get("retry_count", 0),
                "execution_time": metrics.get("execution_time"),
                "agent_name": metrics.get("agent_name"),
                "context": metrics.get("context", {})
            }
            
            # Store in memory
            memory_manager.set(
                f"failure_trace_{task_id}_{datetime.now().timestamp()}",
                failure_trace,
                segment="system"
            )
            
            # Update aggregate failure patterns
            self._update_failure_patterns(failure_trace)
            
        except Exception as e:
            logger.error(f"Failed to log failure trace: {e}")
            
    def _update_failure_patterns(self, failure_trace: Dict[str, Any]) -> None:
        """
        Update aggregate failure patterns for long-term learning.
        
        Args:
            failure_trace: The current failure trace
        """
        try:
            # Skip if we don't have memory access
            if not hasattr(self.metrics_service, "memory_manager"):
                return
                
            memory_manager = self.metrics_service.memory_manager
            if not memory_manager:
                return
                
            # Get current patterns or create new ones
            patterns_key = "failure_patterns"
            patterns = memory_manager.get(patterns_key, segment="system") or {
                "total_failures": 0,
                "by_error": {},
                "by_action": {},
                "by_agent": {},
                "recent_failures": []
            }
            
            # Update counts
            patterns["total_failures"] += 1
            
            # By error type
            error = failure_trace.get("error", "Unknown error")
            patterns["by_error"].setdefault(error, 0)
            patterns["by_error"][error] += 1
            
            # By recovery action
            action = failure_trace.get("recovery_action")
            if action:
                patterns["by_action"].setdefault(action, 0)
                patterns["by_action"][action] += 1
                
            # By agent
            agent = failure_trace.get("agent_name")
            if agent:
                patterns["by_agent"].setdefault(agent, 0)
                patterns["by_agent"][agent] += 1
                
            # Keep track of recent failures (last 20)
            patterns["recent_failures"].append(failure_trace)
            if len(patterns["recent_failures"]) > 20:
                patterns["recent_failures"].pop(0)
                
            # Save updated patterns
            memory_manager.set(patterns_key, patterns, segment="system")
            
        except Exception as e:
            logger.error(f"Failed to update failure patterns: {e}")
    
    def _update_strategy_performance(self, action: str, success: bool, execution_time: float):
        """Update performance metrics for a strategy."""
        if action not in self.strategies:
            return
            
        performance = self.performance_cache.get(action, {
            "success_rate": 0.0,
            "avg_time": 0.0,
            "attempts": 0
        })
        
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
        
        self.performance_cache[action] = performance
        self._update_strategy_weight(action)
    
    def _get_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for all strategies."""
        return {
            action: {
                "success_rate": stats["success_rate"],
                "avg_time": stats["avg_time"],
                "weight": self.strategies[action]["weight"],
                "attempts": stats.get("attempts", 0)
            }
            for action, stats in self.performance_cache.items()
            if action in self.strategies
        }
    
    def _get_active_recoveries(self) -> List[Dict[str, Any]]:
        """Get list of tasks currently in recovery state."""
        active_recoveries = []
        
        for task_id, metrics in self.metrics_service.metrics_cache.items():
            if metrics["status_history"]:
                last_status = metrics["status_history"][-1]
                if last_status["status"] in ["recovering", "stalled"]:
                    active_recoveries.append({
                        "task_id": task_id,
                        "metrics": metrics,
                        "last_status": last_status
                    })
        
        return active_recoveries
    
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
        for action in self.strategies:
            if action not in self.performance_cache:
                recommendations.append(f"Strategy '{action}' has never been used - consider removal")
        
        return recommendations
    
    def _handle_max_retries_exceeded(self, task_id: str, retry_count: int):
        """Handle case where maximum retries have been exceeded."""
        error_msg = f"Task {task_id} failed after {retry_count} retries (Max retries exceeded)"
        logger.error(error_msg)
        
        self._update_task_metrics(
            task_id,
            "failed",
            error=error_msg,
            retry_count=retry_count
        )
    
    def start_auto_tuning_loop(self, interval_seconds: int = 3600) -> None:
        """
        Start background thread for periodic strategy tuning.
        
        Args:
            interval_seconds: Interval between strategy tuning runs in seconds
        """
        import threading
        
        def tuning_loop():
            while True:
                try:
                    # Tune strategies and save
                    self.tune_strategies()
                    # Wait for next interval
                    time.sleep(interval_seconds)
                except Exception as e:
                    logger.error(f"Error in strategy tuning loop: {e}")
                    time.sleep(interval_seconds)  # Still wait even on error
                
        # Start tuning thread as daemon so it doesn't prevent app shutdown
        tuning_thread = threading.Thread(
            target=tuning_loop,
            daemon=True,
            name="RecoveryStrategyTuning"
        )
        tuning_thread.start()
        logger.info(f"Strategy auto-tuning loop started (interval: {interval_seconds}s)")
        
    def tune_strategies(self) -> None:
        """
        Tune recovery strategies by:
        1. Pruning low-performing strategies
        2. Adjusting weights based on success rates
        3. Generating new potential strategies
        4. Saving updated strategies to configuration
        """
        try:
            # Skip if no metrics are available
            if not self.metrics_service:
                return
                
            logger.info("Starting recovery strategy tuning...")
            
            # Get current performance metrics
            self._update_performance_metrics()
            
            # Prune low-weight strategies if they've been used enough times
            pruned_count = self._prune_low_weight_strategies()
            
            # Generate new strategies
            new_strategies = self._generate_new_strategies()
            
            # Save updated strategies
            self._save_strategies()
                
            logger.info(
                f"Strategy tuning complete. Pruned: {pruned_count}, "
                f"New: {len(new_strategies)}, "
                f"Total: {len(self.strategies)}"
            )
        except Exception as e:
            logger.error(f"Failed to tune strategies: {e}")
            
    def _prune_low_weight_strategies(self, min_weight: float = 0.2, min_attempts: int = 5) -> int:
        """
        Prune strategies with consistently low weights after sufficient attempts.
        
        Args:
            min_weight: Minimum weight threshold
            min_attempts: Minimum number of attempts before pruning
            
        Returns:
            Number of pruned strategies
        """
        to_prune = []
        
        metrics = self.metrics_service.get_global_metrics()
        action_stats = metrics.get("recovery_action_stats", {})
        
        for action, stats in self.strategies.items():
            # Skip core strategies that should always be available
            if action in ["start_new_chat", "reload_context", "reset_cursor"]:
                continue
                
            # Check if strategy has been used enough times
            if action in action_stats and action_stats[action]["attempts"] >= min_attempts:
                if stats["weight"] < min_weight:
                    to_prune.append(action)
                    logger.info(
                        f"Marking strategy '{action}' for pruning: "
                        f"weight={stats['weight']:.2f}, "
                        f"attempts={action_stats[action]['attempts']}"
                    )
        
        # Remove pruned strategies
        for action in to_prune:
            del self.strategies[action]
            
        return len(to_prune)
        
    def _generate_new_strategies(self) -> List[str]:
        """
        Generate new recovery strategies based on pattern analysis.
        
        Returns:
            List of new strategy names
        """
        new_strategies = []
        
        # Skip if we don't have memory access
        if not hasattr(self.metrics_service, "memory_manager"):
            return new_strategies
            
        memory_manager = self.metrics_service.memory_manager
        if not memory_manager:
            return new_strategies
            
        # Get failure patterns
        patterns = memory_manager.get("failure_patterns", segment="system")
        if not patterns:
            return new_strategies
            
        # Analyze recent failures to identify new strategy opportunities
        recent_failures = patterns.get("recent_failures", [])
        error_counts = patterns.get("by_error", {})
        
        # Create new composite strategy if we see common error sequences
        error_sequences = self._identify_error_sequences(recent_failures)
        for seq, count in error_sequences.items():
            if count >= 3 and seq not in self.strategies:
                # Create composite strategy
                new_strategy_name = f"composite_{seq.replace(' ', '_')}"
                if new_strategy_name not in self.strategies:
                    self.strategies[new_strategy_name] = {
                        "description": f"Composite strategy for sequence: {seq}",
                        "weight": 0.5,  # Initial weight
                        "conditions": ["stalled", seq],
                        "dependencies": [],
                        "actions": [
                            "reload_context",
                            "reset_cursor"
                        ]
                    }
                    new_strategies.append(new_strategy_name)
                    logger.info(f"Created new composite strategy '{new_strategy_name}'")
            
        # Create specialized strategies for frequent errors
        for error, count in error_counts.items():
            if count >= 5:
                error_type = self._categorize_error(error)
                if error_type and error_type not in self.strategies:
                    new_strategy_name = f"handle_{error_type}"
                    if new_strategy_name not in self.strategies:
                        self.strategies[new_strategy_name] = {
                            "description": f"Handle {error_type} errors",
                            "weight": 0.5,  # Initial weight
                            "conditions": [error_type],
                            "dependencies": [],
                            "actions": [
                                "reload_context"
                            ]
                        }
                        new_strategies.append(new_strategy_name)
                        logger.info(f"Created new error-specific strategy '{new_strategy_name}'")
        
        return new_strategies
        
    def _identify_error_sequences(self, recent_failures: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Identify common sequences of errors.
        
        Args:
            recent_failures: List of recent failure traces
            
        Returns:
            Dictionary mapping error sequences to frequency
        """
        sequences = {}
        
        # Skip if fewer than 3 failures
        if len(recent_failures) < 3:
            return sequences
            
        # Sort failures by timestamp
        sorted_failures = sorted(
            recent_failures, 
            key=lambda x: x.get("timestamp", "")
        )
        
        # Look for sequences of 2 errors
        for i in range(len(sorted_failures) - 1):
            error1 = self._categorize_error(sorted_failures[i].get("error", ""))
            error2 = self._categorize_error(sorted_failures[i + 1].get("error", ""))
            
            if error1 and error2:
                seq = f"{error1}_then_{error2}"
                sequences[seq] = sequences.get(seq, 0) + 1
                
        return sequences
        
    def _categorize_error(self, error_message: str) -> Optional[str]:
        """
        Categorize an error message into a standardized type.
        
        Args:
            error_message: Raw error message
            
        Returns:
            Categorized error type or None
        """
        error_message = error_message.lower()
        
        for category, patterns in self.error_categories.items():
            if any(pattern in error_message for pattern in patterns):
                return category
                
        return "other"
    
    def _save_strategies(self) -> bool:
        """Save recovery strategies to the config file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.strategies, f, indent=2)
            logger.info(f"Saved strategies to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save strategies to {self.config_path}: {e}")
            return False
    
    def suggest_new_strategies(self) -> List[Dict[str, Any]]:
        """
        Suggest new recovery strategies based on performance patterns.
        
        This is part of the self-tuning capability:
        - Identifies gaps in coverage
        - Proposes new strategies for errors not well handled
        - Refines conditions for existing strategies
        """
        suggestions = []
        
        # Analyze error categories not well covered
        covered_error_types = set()
        for strategy in self.strategies.values():
            for condition in strategy.get("conditions", []):
                if "error_type ==" in condition:
                    error_type = condition.split("==")[1].strip().strip("'\"")
                    covered_error_types.add(error_type)
        
        # Suggest new strategies for uncovered error types
        for error_type in self.error_categories.keys():
            if error_type not in covered_error_types:
                suggestions.append({
                    "action": f"new_strategy_for_{error_type}",
                    "suggestion_type": "new_strategy",
                    "template": {
                        "weight": 0.5,
                        "conditions": [f"error_type == '{error_type}'"],
                        "success_rate": 0.0,
                        "attempts": 0,
                        "successes": 0
                    }
                })
        
        return suggestions
    
    def prune_low_performing_strategies(self, threshold: float = 0.2, min_attempts: int = 10) -> List[str]:
        """
        Identify and prune low-performing strategies.
        
        Args:
            threshold: Success rate threshold below which to consider pruning
            min_attempts: Minimum number of attempts before considering pruning
            
        Returns:
            List of strategy names that were pruned
        """
        pruned = []
        
        for action, strategy in list(self.strategies.items()):
            attempts = strategy.get("attempts", 0)
            if attempts >= min_attempts:
                success_rate = strategy.get("success_rate", 0)
                if success_rate < threshold:
                    # Don't delete, but reduce weight significantly
                    self.strategies[action]["weight"] = max(0.1, self.strategies[action]["weight"] * 0.5)
                    pruned.append(action)
                    logger.info(f"Reduced weight for low-performing strategy: {action}")
        
        # Save changes
        if pruned:
            self._save_strategies()
            
        return pruned
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for all recovery strategies."""
        # Update metrics before returning
        self._update_performance_metrics()
        
        # Add strategy-specific details
        strategy_stats = {}
        for action, strategy in self.strategies.items():
            strategy_stats[action] = {
                "weight": strategy.get("weight", 0),
                "success_rate": strategy.get("success_rate", 0),
                "attempts": strategy.get("attempts", 0),
                "successes": strategy.get("successes", 0),
                "avg_execution_time": sum(strategy.get("execution_times", [])) / len(strategy.get("execution_times", [1])) if strategy.get("execution_times") else 0
            }
        
        return {
            **self.performance_cache,
            "strategies": strategy_stats
        } 