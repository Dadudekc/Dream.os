import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from threading import Lock
from core.PathManager import PathManager

logger = logging.getLogger(__name__)

class SystemState:
    """
    Manages the state of the prompt cycle system.
    Tracks system metrics, events, and configuration.
    """
    
    def __init__(self):
        """Initialize the system state manager."""
        self.lock = Lock()
        
        # Use PathManager for file paths
        self.state_file = PathManager.get_path('memory', 'system_state.json')
        
        # Initialize system state
        self.state = {
            "version": 1,
            "last_updated": datetime.now().isoformat(),
            "metrics": {
                "total_prompts_processed": 0,
                "total_tokens_used": 0,
                "total_interactions": 0,
                "total_insights": 0
            },
            "events": [],
            "configuration": {
                "active_model": "gpt-4o",
                "cycle_speed": 2,
                "log_level": "info"
            }
        }
        
        # Load existing state if available
        self._load_state()
    
    def _load_state(self) -> None:
        """Load system state from file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.state = data
                    logger.info(f"Loaded system state from {self.state_file}")
            else:
                logger.info("No system state file found. Starting with default state.")
        except Exception as e:
            logger.error(f"Failed to load system state: {e}")
    
    def _save_state(self) -> None:
        """Save system state to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2)
                logger.info(f"Saved system state to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save system state: {e}")
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get the current system state.
        
        Returns:
            Dictionary containing the full system state
        """
        with self.lock:
            return self.state.copy()
    
    def update_state(self, new_state: Dict[str, Any]) -> None:
        """
        Update the system state with new values.
        
        Args:
            new_state: Dictionary containing state updates
        """
        with self.lock:
            # Deep merge of nested dictionaries
            self._deep_merge(self.state, new_state)
            
            # Update last_updated timestamp
            self.state["last_updated"] = datetime.now().isoformat()
            
            # Save the updated state
            self._save_state()
    
    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Deep merge source dictionary into target dictionary.
        
        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
    
    def increment_metric(self, metric_name: str, value: int = 1) -> None:
        """
        Increment a numeric metric.
        
        Args:
            metric_name: Name of the metric to increment
            value: Amount to increment by (default: 1)
        """
        with self.lock:
            if metric_name in self.state["metrics"]:
                self.state["metrics"][metric_name] += value
            else:
                self.state["metrics"][metric_name] = value
                
            self.state["last_updated"] = datetime.now().isoformat()
            self._save_state()
    
    def add_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Add an event to the system state.
        
        Args:
            event_type: Type of event (e.g., 'prompt_processed', 'insight_added')
            event_data: Data associated with the event
        """
        with self.lock:
            event = {
                "type": event_type,
                "timestamp": datetime.now().isoformat(),
                "data": event_data
            }
            
            self.state["events"].append(event)
            
            # Limit events list size to prevent unbounded growth
            if len(self.state["events"]) > 100:
                self.state["events"] = self.state["events"][-100:]
                
            self.state["last_updated"] = datetime.now().isoformat()
            self._save_state()
    
    def update_configuration(self, config_updates: Dict[str, Any]) -> None:
        """
        Update system configuration.
        
        Args:
            config_updates: Dictionary containing configuration updates
        """
        with self.lock:
            self.state["configuration"].update(config_updates)
            self.state["last_updated"] = datetime.now().isoformat()
            self._save_state()
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current system metrics.
        
        Returns:
            Dictionary of metrics
        """
        with self.lock:
            return self.state["metrics"].copy()
    
    def get_events(self, limit: int = 10, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent system events.
        
        Args:
            limit: Maximum number of events to return
            event_type: Optional filter by event type
            
        Returns:
            List of event dictionaries
        """
        with self.lock:
            events = self.state["events"]
            
            if event_type:
                events = [e for e in events if e["type"] == event_type]
                
            # Return most recent events first
            return list(reversed(events))[:limit]
    
    def get_configuration(self) -> Dict[str, Any]:
        """
        Get current system configuration.
        
        Returns:
            Dictionary of configuration settings
        """
        with self.lock:
            return self.state["configuration"].copy()
    
    def reset_state(self) -> None:
        """Reset system state to default values."""
        with self.lock:
            self.state = {
                "version": self.state["version"] + 1,
                "last_updated": datetime.now().isoformat(),
                "metrics": {
                    "total_prompts_processed": 0,
                    "total_tokens_used": 0,
                    "total_interactions": 0,
                    "total_insights": 0
                },
                "events": [],
                "configuration": self.state["configuration"]
            }
            self._save_state()
    
    def generate_system_report(self) -> Dict[str, Any]:
        """
        Generate a system state report.
        
        Returns:
            Dictionary containing the system report
        """
        with self.lock:
            report = {
                "timestamp": datetime.now().isoformat(),
                "version": self.state["version"],
                "metrics": self.state["metrics"],
                "recent_events": self.get_events(5),
                "configuration": self.state["configuration"]
            }
            
            # Save report to file
            report_file = PathManager.get_path('outputs', 'system_report.json')
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(report_file), exist_ok=True)
                
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2)
                    logger.info(f"System report saved to {report_file}")
            except Exception as e:
                logger.error(f"Failed to save system report: {e}")
            
            return report 