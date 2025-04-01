"""
Feedback Engine module for managing feedback.
"""
from typing import Optional, Any, Dict, List
import logging
import json
import os
from datetime import datetime
from core.memory import FeedbackEntry

logger = logging.getLogger(__name__)

class FeedbackEngine:
    """Engine for managing feedback."""
    
    def __init__(
        self,
        prompt_manager: Any,
        config: Any,
        logger: Optional[logging.Logger] = None,
        recovery_engine: Optional[Any] = None
    ):
        """
        Initialize the feedback engine.
        
        Args:
            prompt_manager: The prompt manager instance
            config: The configuration manager
            logger: Optional logger instance
            recovery_engine: Optional recovery engine instance
        """
        self.prompt_manager = prompt_manager
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.recovery_engine = recovery_engine
        self.feedback_entries = []
        self.feedback_log_file = "memory/feedback_log.json"
        
        # Load existing feedback if available
        self._load_feedback()
        
    def add_feedback(self, feedback_type: str, content: str, metadata: Optional[Dict] = None) -> Optional[FeedbackEntry]:
        """
        Add a feedback entry.
        
        Args:
            feedback_type: Type of feedback
            content: Feedback content
            metadata: Optional metadata
            
        Returns:
            The created feedback entry or None
        """
        try:
            # Generate unique ID
            entry_id = f"fb_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.feedback_entries) + 1}"
            
            # Create entry
            entry = FeedbackEntry(
                id=entry_id,
                type=feedback_type,
                content=content,
                metadata=metadata or {}
            )
            
            # Enrich with recovery metrics if available
            self._enrich_with_recovery_metrics(entry)
            
            # Add to memory and log
            self.feedback_entries.append(entry)
            self._save_feedback()
            
            self.logger.info(f"Added feedback entry: {entry.id}")
            return entry
            
        except Exception as e:
            self.logger.error(f"Error adding feedback: {e}")
            return None
            
    def get_feedback(self, feedback_id: str) -> Optional[FeedbackEntry]:
        """
        Get a feedback entry.
        
        Args:
            feedback_id: The feedback ID
            
        Returns:
            The feedback entry or None
        """
        try:
            for entry in self.feedback_entries:
                if entry.id == feedback_id:
                    return entry
            return None
        except Exception as e:
            self.logger.error(f"Error getting feedback: {e}")
            return None
            
    def get_all_feedback(self) -> List[FeedbackEntry]:
        """
        Get all feedback entries.
        
        Returns:
            List of all feedback entries
        """
        return self.feedback_entries
        
    def get_recovery_enhanced_score(self, prompt_id: str, raw_score: float) -> float:
        """
        Get a score for a prompt that incorporates recovery metrics.
        
        Args:
            prompt_id: ID of the prompt
            raw_score: Raw score from feedback
            
        Returns:
            Enhanced score that considers recovery metrics
        """
        try:
            if not self.recovery_engine:
                return raw_score
                
            # Get recovery stats for this prompt
            stats = self.recovery_engine.get_recovery_stats()
            
            # Get prompt-specific metrics
            prompt_metrics = self._get_prompt_recovery_metrics(prompt_id, stats)
            
            # Calculate penalty based on recovery metrics
            recovery_factor = self._calculate_recovery_factor(prompt_metrics)
            
            # Apply recovery factor (weighted 70% raw score, 30% recovery)
            enhanced_score = (raw_score * 0.7) + (recovery_factor * 0.3)
            
            self.logger.debug(
                f"Enhanced score for {prompt_id}: {enhanced_score:.2f} "
                f"(raw={raw_score:.2f}, recovery_factor={recovery_factor:.2f})"
            )
            
            return enhanced_score
            
        except Exception as e:
            self.logger.error(f"Error calculating enhanced score: {e}")
            return raw_score
            
    def _get_prompt_recovery_metrics(self, prompt_id: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract recovery metrics relevant to a specific prompt.
        
        Args:
            prompt_id: ID of the prompt
            stats: Global recovery statistics
            
        Returns:
            Dictionary of recovery metrics for this prompt
        """
        # Default metrics
        prompt_metrics = {
            "failures": 0,
            "recoveries": 0,
            "recovery_time": 0.0,
            "recovery_attempts": 0
        }
        
        # Check active recoveries
        for recovery in stats.get("active_recoveries", []):
            if recovery.get("metrics", {}).get("prompt_id") == prompt_id:
                prompt_metrics["failures"] += 1
                
        # Check global metrics for this prompt
        global_metrics = stats.get("global_metrics", {})
        for task_id, metrics in global_metrics.items():
            if metrics.get("prompt_id") == prompt_id:
                if metrics.get("status") == "error":
                    prompt_metrics["failures"] += 1
                elif metrics.get("status") == "recovered":
                    prompt_metrics["recoveries"] += 1
                    prompt_metrics["recovery_time"] += metrics.get("execution_time", 0.0)
                    prompt_metrics["recovery_attempts"] += 1
                    
        # Calculate average recovery time
        if prompt_metrics["recovery_attempts"] > 0:
            prompt_metrics["avg_recovery_time"] = prompt_metrics["recovery_time"] / prompt_metrics["recovery_attempts"]
        else:
            prompt_metrics["avg_recovery_time"] = 0.0
            
        return prompt_metrics
        
    def _calculate_recovery_factor(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate a recovery factor (0-1) based on recovery metrics.
        
        Args:
            metrics: Recovery metrics for a prompt
            
        Returns:
            Recovery factor between 0 and 1
        """
        # No failures is a perfect score
        if metrics["failures"] == 0:
            return 1.0
            
        # Calculate recovery success rate
        if metrics["failures"] > 0:
            recovery_rate = metrics["recoveries"] / metrics["failures"]
        else:
            recovery_rate = 1.0
            
        # Penalize for slow recovery
        time_factor = 1.0
        if metrics["avg_recovery_time"] > 0:
            time_factor = min(1.0, 10.0 / (metrics["avg_recovery_time"] + 1.0))
            
        # Combine factors (weighted 80% recovery rate, 20% time)
        recovery_factor = (recovery_rate * 0.8) + (time_factor * 0.2)
        
        # Ensure range is between 0 and 1
        return max(0.0, min(1.0, recovery_factor))
        
    def _enrich_with_recovery_metrics(self, entry: FeedbackEntry) -> None:
        """
        Enrich a feedback entry with recovery metrics.
        
        Args:
            entry: The feedback entry to enrich
        """
        if not self.recovery_engine:
            return
            
        try:
            # Get recovery stats
            stats = self.recovery_engine.get_recovery_stats()
            
            # Add recovery metrics to metadata
            entry.metadata = entry.metadata or {}
            entry.metadata["recovery_metrics"] = {
                "collected_at": datetime.now().isoformat(),
                "global_recovery_rate": self._calculate_global_recovery_rate(stats),
                "active_recoveries": len(stats.get("active_recoveries", [])),
                "recommendations": stats.get("recommendations", [])
            }
            
        except Exception as e:
            self.logger.error(f"Error enriching feedback with recovery metrics: {e}")
            
    def _calculate_global_recovery_rate(self, stats: Dict[str, Any]) -> float:
        """
        Calculate global recovery success rate from stats.
        
        Args:
            stats: Recovery statistics
            
        Returns:
            Recovery success rate (0-1)
        """
        global_metrics = stats.get("global_metrics", {})
        total_failures = 0
        total_recoveries = 0
        
        for task_id, metrics in global_metrics.items():
            if metrics.get("status") == "error":
                total_failures += 1
            elif metrics.get("status") == "recovered":
                total_recoveries += 1
                
        if total_failures + total_recoveries > 0:
            return total_recoveries / (total_failures + total_recoveries)
        else:
            return 1.0
            
    def _load_feedback(self) -> None:
        """Load feedback entries from file."""
        try:
            if os.path.exists(self.feedback_log_file):
                with open(self.feedback_log_file, 'r') as f:
                    entries_data = json.load(f)
                    self.feedback_entries = [
                        FeedbackEntry.from_dict(entry) for entry in entries_data
                    ]
                self.logger.info(f"Loaded {len(self.feedback_entries)} feedback entries")
        except Exception as e:
            self.logger.error(f"Error loading feedback: {e}")
            
    def _save_feedback(self) -> None:
        """Save feedback entries to file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.feedback_log_file), exist_ok=True)
            
            # Save entries
            with open(self.feedback_log_file, 'w') as f:
                entries_data = [entry.to_dict() for entry in self.feedback_entries]
                json.dump(entries_data, f, indent=2)
                
            self.logger.debug(f"Saved {len(self.feedback_entries)} feedback entries")
        except Exception as e:
            self.logger.error(f"Error saving feedback: {e}")
            
    def register_failure_hooks(self, failure_hook) -> None:
        """
        Register failure handlers with the hook system.
        
        Args:
            failure_hook: The AgentFailureHook instance
        """
        if not failure_hook:
            return
            
        # Handler for feedback errors
        def handle_feedback_error(error_type: str, context: Dict[str, Any]) -> bool:
            try:
                if error_type == "feedback_error":
                    self.logger.warning("Attempting to recover from feedback error...")
                    # Add error entry to record the issue
                    self.add_feedback(
                        feedback_type="error",
                        content=f"Feedback error: {context.get('error', 'Unknown error')}",
                        metadata={"error_context": context}
                    )
                    return True
                return False
            except Exception as e:
                self.logger.error(f"Feedback error handler failed: {e}")
                return False
                
        # Register handlers
        failure_hook.register_handler(
            agent_name="feedback_engine",
            handler=handle_feedback_error,
            error_types=["feedback_error"]
        ) 