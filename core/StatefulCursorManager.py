"""
StatefulCursorManager.py - Enhanced cursor session manager with state persistence

Extends the base CursorSessionManager to add state persistence capabilities.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
import threading
import time

# Import existing cursor session manager
from core.CursorSessionManager import CursorSessionManager

logger = logging.getLogger(__name__)

class StatefulCursorManager(CursorSessionManager):
    """
    Enhanced Cursor Session Manager with persistent state capabilities.
    
    Extends CursorSessionManager to maintain context between sessions, allowing
    for more intelligent code improvements over time.
    
    Key enhancements:
    - Persistent session state that survives restarts
    - Module-level improvement tracking
    - Metrics history to identify improvement patterns
    - Context-aware prompt generation
    """
    
    def __init__(self, config_manager=None, state_file_path: Optional[str] = None):
        """
        Initialize the StatefulCursorManager with both session management and state persistence.
        
        Args:
            config_manager: Optional configuration manager
            state_file_path: Optional path to the state file (defaults to memory/cursor_state.json)
        """
        # Initialize the base cursor session manager
        super().__init__()
        
        # Store config manager
        self.config_manager = config_manager
        
        # Set up state file path
        self.state_file = Path(state_file_path or "memory/cursor_state.json")
        
        # Initialize state with defaults
        self.state = {
            "last_session_time": None,
            "session_count": 0,
            "improvement_history": [],
            "context": {},
            "metrics_history": [],
            "module_stats": {},
            "active_improvements": {}
        }
        
        # Initialize state lock for thread safety
        self.state_lock = threading.RLock()
        
        # Load existing state if available
        self.load_state()
        
        # Add periodic state auto-save
        self._start_state_save_timer()
        
        # Try to load priority weighting config if available
        try:
            from priority_weighting_config import PriorityWeightingConfig
            self.priority_config = PriorityWeightingConfig()
            logger.info("Loaded priority weighting configuration")
        except ImportError:
            self.priority_config = None
            logger.info("Priority weighting configuration not available")
        
        logger.info("StatefulCursorManager initialized with persistence")
    
    def _start_state_save_timer(self):
        """Start a timer to periodically save state."""
        self.state_save_timer = threading.Timer(300, self._auto_save_state)  # Save every 5 minutes
        self.state_save_timer.daemon = True
        self.state_save_timer.start()
    
    def _auto_save_state(self):
        """Automatically save state and reschedule next save."""
        self.save_state()
        
        # Reschedule next save
        self.state_save_timer = threading.Timer(300, self._auto_save_state)
        self.state_save_timer.daemon = True
        self.state_save_timer.start()
    
    def load_state(self) -> Dict[str, Any]:
        """
        Load cursor session state from disk.
        
        Returns:
            Dict[str, Any]: The loaded state
        """
        with self.state_lock:
            try:
                if self.state_file.exists():
                    with open(self.state_file, 'r', encoding='utf-8') as f:
                        loaded_state = json.load(f)
                        self.state.update(loaded_state)
                        logger.info(f"Loaded cursor session state: {len(self.state)} keys")
                else:
                    logger.info("No previous session state found. Starting fresh.")
            except Exception as e:
                logger.error(f"Error loading session state: {e}")
            
            return self.state
    
    def save_state(self) -> bool:
        """
        Save cursor session state to disk.
        
        Returns:
            bool: True if successful, False otherwise
        """
        with self.state_lock:
            try:
                # Update session metadata
                self.state["last_session_time"] = datetime.now().isoformat()
                self.state["session_count"] += 1
                
                # Ensure directory exists
                self.state_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Write state to disk
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    json.dump(self.state, f, indent=2)
                    
                logger.info(f"Saved cursor session state. Session count: {self.state['session_count']}")
                return True
            except Exception as e:
                logger.error(f"Error saving session state: {e}")
                return False
    
    def update_context(self, module: str, key: str, value: Any) -> None:
        """
        Update a specific context value for a module in the state.
        
        Args:
            module: Module or file name
            key: Context key
            value: Context value
        """
        with self.state_lock:
            if "context" not in self.state:
                self.state["context"] = {}
            
            if module not in self.state["context"]:
                self.state["context"][module] = {}
            
            self.state["context"][module][key] = value
            logger.debug(f"Updated context for {module}: {key}")
    
    def get_context(self, module: str, key: str, default: Any = None) -> Any:
        """
        Get a specific context value for a module from the state.
        
        Args:
            module: Module or file name
            key: Context key
            default: Default value if not found
            
        Returns:
            Any: The context value or default
        """
        with self.state_lock:
            module_context = self.state.get("context", {}).get(module, {})
            return module_context.get(key, default)
    
    def add_improvement_record(self, module: str, changes: Dict[str, Any], metrics_before: Dict[str, Any], 
                             metrics_after: Dict[str, Any]) -> None:
        """
        Record an improvement made to the codebase with before/after metrics.
        
        Args:
            module: The module or file name
            changes: Description of changes made
            metrics_before: Metrics before the change
            metrics_after: Metrics after the change
        """
        with self.state_lock:
            if "improvement_history" not in self.state:
                self.state["improvement_history"] = []
                
            # Calculate metrics delta
            metrics_delta = {}
            for key in set(metrics_before.keys()) | set(metrics_after.keys()):
                before_val = metrics_before.get(key, 0)
                after_val = metrics_after.get(key, 0)
                metrics_delta[key] = after_val - before_val
                
            record = {
                "timestamp": datetime.now().isoformat(),
                "module": module,
                "changes": changes,
                "metrics_before": metrics_before,
                "metrics_after": metrics_after,
                "metrics_delta": metrics_delta
            }
            
            self.state["improvement_history"].append(record)
            
            # Also update module stats
            if "module_stats" not in self.state:
                self.state["module_stats"] = {}
                
            if module not in self.state["module_stats"]:
                self.state["module_stats"][module] = {
                    "improvement_count": 0,
                    "last_improved": None,
                    "complexity_delta": 0,
                    "coverage_delta": 0
                }
                
            # Update module stats
            mod_stats = self.state["module_stats"][module]
            mod_stats["improvement_count"] += 1
            mod_stats["last_improved"] = datetime.now().isoformat()
            
            # Calculate metric deltas if available
            if metrics_before and metrics_after:
                complexity_before = metrics_before.get("complexity", 0)
                complexity_after = metrics_after.get("complexity", 0)
                coverage_before = metrics_before.get("coverage", 0)
                coverage_after = metrics_after.get("coverage", 0)
                
                mod_stats["complexity_delta"] += (complexity_after - complexity_before)
                mod_stats["coverage_delta"] += (coverage_after - coverage_before)
                
            logger.info(f"Recorded improvement for {module}")
    
    def get_module_history(self, module: str) -> List[Dict[str, Any]]:
        """
        Get improvement history for a specific module.
        
        Args:
            module: Module name
            
        Returns:
            List[Dict[str, Any]]: List of improvement records
        """
        with self.state_lock:
            return [record for record in self.state.get("improvement_history", []) 
                    if record.get("module") == module]
    
    def update_metrics_history(self, metrics_data: Dict[str, Any]) -> None:
        """
        Update metrics history with new data.
        
        Args:
            metrics_data: Dictionary of metrics
        """
        with self.state_lock:
            if "metrics_history" not in self.state:
                self.state["metrics_history"] = []
                
            record = {
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics_data
            }
            
            self.state["metrics_history"].append(record)
            logger.info("Metrics history updated")
    
    def get_latest_metrics(self, module: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the latest metrics for a module, or all metrics if no module specified.
        
        Args:
            module: Optional module name
            
        Returns:
            Dict[str, Any]: Latest metrics
        """
        with self.state_lock:
            if not self.state.get("metrics_history"):
                return {}
                
            # Get the most recent metrics entry
            latest = self.state["metrics_history"][-1]["metrics"]
            
            if module:
                # Return only the specified module metrics
                return latest.get(module, {})
            
            return latest
    
    def get_improvement_candidates(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get modules that are candidates for improvement based on metrics.
        
        Args:
            count: Number of candidates to return
            
        Returns:
            List[Dict[str, Any]]: List of modules with scores
        """
        with self.state_lock:
            candidates = []
            
            # Get latest metrics
            latest_metrics = self.get_latest_metrics()
            
            # Get module stats
            module_stats = self.state.get("module_stats", {})
            
            # Build candidates list
            for module, metrics in latest_metrics.items():
                # Skip modules currently being improved
                if module in self.state.get("active_improvements", {}):
                    continue
                    
                # Get module's improvement history
                history = self.get_module_history(module)
                
                # Get metrics
                complexity = metrics.get("complexity", 0)
                coverage = metrics.get("coverage_percentage", 0)
                maintainability = metrics.get("maintainability_index", 0)
                
                # Basic scoring algorithm - higher complexity, lower coverage,
                # lower maintainability, and less frequent improvements get higher scores
                last_improved = None
                if module in module_stats:
                    last_improved = module_stats[module].get("last_improved")
                
                # Calculate days since last improvement
                days_since_improvement = 1000  # Default to a high number if never improved
                if last_improved:
                    last_date = datetime.fromisoformat(last_improved)
                    days_since_improvement = (datetime.now() - last_date).days
                
                # Add days_since_improvement to metrics for priority weighting
                metrics["days_since_improvement"] = days_since_improvement
                
                # Use priority weighting if available
                if self.priority_config:
                    try:
                        score = self.priority_config.calculate_module_score(metrics)
                        logger.debug(f"Using priority weights for {module}: score={score}")
                    except Exception as e:
                        logger.error(f"Error using priority weights: {e}")
                        # Fall back to default scoring
                        score = self._calculate_default_score(complexity, coverage, maintainability, days_since_improvement)
                else:
                    # Use default scoring
                    score = self._calculate_default_score(complexity, coverage, maintainability, days_since_improvement)
                
                candidates.append({
                    "module": module,
                    "score": score,
                    "last_improved": last_improved,
                    "days_since_improvement": days_since_improvement
                })
            
            # Sort by score (higher score first)
            candidates.sort(key=lambda x: x["score"], reverse=True)
            
            return candidates[:count]
    
    def _calculate_default_score(self, complexity: float, coverage: float, maintainability: float, days_since_improvement: int) -> float:
        """
        Calculate a default improvement score without using priority weights.
        
        Args:
            complexity: Complexity metric
            coverage: Coverage percentage
            maintainability: Maintainability index
            days_since_improvement: Days since last improvement
            
        Returns:
            float: Improvement score
        """
        return (
            complexity * 2 +                        # Higher complexity = higher score
            max(0, (100 - coverage)) * 1.5 +       # Lower coverage = higher score
            max(0, (100 - maintainability)) +      # Lower maintainability = higher score
            min(days_since_improvement * 0.5, 50)  # More days since improvement = higher score
        )
    
    def get_latest_prompt_context(self, module: Optional[str] = None) -> str:
        """
        Get context-aware prompt based on session history and metrics.
        
        Args:
            module: Optional module name to focus on
            
        Returns:
            str: Context information for prompts
        """
        with self.state_lock:
            context_parts = []
            
            if module:
                # Add module-specific context
                module_context = self.state.get("context", {}).get(module, {})
                if module_context:
                    context_parts.append(f"Module Context for {module}:")
                    for key, value in module_context.items():
                        context_parts.append(f"- {key}: {value}")
                
                # Add module improvement history
                history = self.get_module_history(module)
                if history:
                    context_parts.append(f"\nImprovement History for {module}:")
                    for idx, record in enumerate(sorted(history, key=lambda x: x["timestamp"]), 1):
                        changes = record.get("changes", {}).get("summary", "No summary")
                        complexity_delta = record.get("metrics_delta", {}).get("complexity", 0)
                        coverage_delta = record.get("metrics_delta", {}).get("coverage", 0)
                        
                        context_parts.append(f"{idx}. {changes}")
                        if complexity_delta != 0:
                            context_parts.append(f"   - Complexity: {complexity_delta:+.2f}")
                        if coverage_delta != 0:
                            context_parts.append(f"   - Coverage: {coverage_delta:+.2f}%")
                            
                # Add latest metrics
                latest_metrics = self.get_latest_metrics(module)
                if latest_metrics:
                    context_parts.append(f"\nCurrent Metrics for {module}:")
                    for key, value in latest_metrics.items():
                        if isinstance(value, (int, float)):
                            context_parts.append(f"- {key}: {value}")
            else:
                # General context about the codebase
                context_parts.append("General Codebase Context:")
                
                # Add overall stats
                metrics_count = len(self.state.get("metrics_history", []))
                improvement_count = len(self.state.get("improvement_history", []))
                
                context_parts.append(f"- Total metrics snapshots: {metrics_count}")
                context_parts.append(f"- Total improvements: {improvement_count}")
                
                # Add top modules by improvement count
                module_stats = self.state.get("module_stats", {})
                if module_stats:
                    top_modules = sorted(
                        module_stats.items(),
                        key=lambda x: x[1].get("improvement_count", 0),
                        reverse=True
                    )[:5]
                    
                    context_parts.append("\nTop Improved Modules:")
                    for module_name, stats in top_modules:
                        context_parts.append(f"- {module_name}: {stats.get('improvement_count', 0)} improvements")
            
            return "\n".join(context_parts)
    
    def mark_module_active(self, module: str) -> None:
        """
        Mark a module as being actively improved.
        
        Args:
            module: Module name
        """
        with self.state_lock:
            if "active_improvements" not in self.state:
                self.state["active_improvements"] = {}
                
            self.state["active_improvements"][module] = {
                "start_time": datetime.now().isoformat(),
                "status": "in_progress"
            }
            
            logger.info(f"Marked {module} as active for improvement")
    
    def mark_module_completed(self, module: str, success: bool = True) -> None:
        """
        Mark a module as completed improvement.
        
        Args:
            module: Module name
            success: Whether the improvement was successful
        """
        with self.state_lock:
            active_improvements = self.state.get("active_improvements", {})
            
            if module in active_improvements:
                del active_improvements[module]
                
                status = "success" if success else "failed"
                logger.info(f"Marked {module} as {status} for improvement")
    
    def get_active_improvements(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all actively improved modules.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of active improvements
        """
        with self.state_lock:
            return self.state.get("active_improvements", {}).copy()
    
    def queue_stateful_prompt(self, module: str, prompt: str, isolation_level: str = "medium", 
                            on_complete: Optional[Callable] = None, timeout: int = 600) -> str:
        """
        Queue a context-aware prompt for execution.
        
        Args:
            module: Module name
            prompt: The prompt to execute
            isolation_level: Isolation level for the prompt
            on_complete: Optional callback when complete
            timeout: Timeout in seconds
            
        Returns:
            str: Session ID
        """
        # Mark module as active
        self.mark_module_active(module)
        
        # Create a wrapper for the on_complete callback
        def on_complete_wrapper(result):
            # Mark module as completed
            self.mark_module_completed(module, success=bool(result))
            
            # Call original callback if provided
            if on_complete:
                on_complete(result)
                
            # Save state
            self.save_state()
        
        # Queue the prompt with the base manager
        session_id = self.queue_prompt(
            prompt, 
            isolation_level=isolation_level,
            on_complete=on_complete_wrapper,
            timeout=timeout
        )
        
        logger.info(f"Queued stateful prompt for {module} with session ID {session_id}")
        return session_id
    
    def _handle_stalled_improvement(self, module: str) -> bool:
        """
        Handle a stalled improvement task.
        
        Args:
            module: Module name
            
        Returns:
            bool: True if handled successfully
        """
        with self.state_lock:
            active_improvements = self.state.get("active_improvements", {})
            
            if module not in active_improvements:
                return False
                
            # Get start time
            start_time_str = active_improvements[module].get("start_time")
            
            if not start_time_str:
                return False
                
            start_time = datetime.fromisoformat(start_time_str)
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # If elapsed time > 1 hour, consider stalled
            if elapsed > 3600:
                # Mark as completed with failure
                self.mark_module_completed(module, success=False)
                
                logger.warning(f"Marked stalled improvement for {module} as failed after {elapsed:.0f} seconds")
                return True
                
            return False 