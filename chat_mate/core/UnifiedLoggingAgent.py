import os
import json
import logging
import threading
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

from core.FileManager import FileManager
from chat_mate.core.interfaces import ILoggingAgent
from chat_mate.core.config.ConfigManager import ConfigManager
from chat_mate.core.PathManager import PathManager

class UnifiedLoggingAgent(ILoggingAgent):
    """
    Centralized logging system for ChatMate that handles all logging operations.
    Features:
    - Thread-safe logging operations
    - Multiple output formats (text, JSON, JSONL)
    - Structured logging with metadata
    - Integration with FileManager for consistent file operations
    - Real-time logging with rotation support
    - Domain-specific logging (AI outputs, social interactions, system events)
    """

    # Logging domains and their specific formats
    DOMAINS = {
        "ai_output": "jsonl",
        "social": "jsonl",
        "system": "text",
        "debug": "text",
        "audit": "jsonl",
        "reinforcement": "jsonl"
    }

    def __init__(self, config_manager):
        """
        Initialize the UnifiedLoggingAgent with necessary components.
        
        Args:
            config_manager: Required ConfigManager instance for configuration access
            
        Raises:
            ValueError: If config_manager is not provided
        """
        if not config_manager:
            raise ValueError("ConfigManager is required for UnifiedLoggingAgent initialization")
            
        self.config_manager = config_manager
        self.file_manager = FileManager()
        self.write_lock = threading.Lock()
        
        # Get logs directory path and ensure it's a string
        self.logs_dir = str(self.config_manager.get('logs_dir', 'outputs/logs'))
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"Logs directory path: {self.logs_dir} (type: {type(self.logs_dir)})")
        
        # Ensure logs directory exists
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Set up the main logger
        self.logger.setLevel(logging.INFO)
        
        # Ensure all log directories exist
        self._setup_log_directories()
        
        # Setup file handler
        self._setup_file_handler()

    def log(self, message: str, domain: str = "system", level: str = "info", metadata: Optional[Dict[str, Any]] = None, tags: Optional[List[str]] = None) -> Optional[str]:
        """
        Log a message with optional metadata and tags.
        
        Args:
            message: The message to log
            domain: The logging domain (e.g., "system", "ai_output", "social")
            level: Logging level (e.g., "info", "error", "debug")
            metadata: Optional dictionary of metadata
            tags: Optional list of tags
            
        Returns:
            Optional[str]: Path to the log file if successful
        """
        if domain not in self.DOMAINS:
            self.logger.warning(f"Unknown logging domain: {domain}. Using 'system' as default.")
            domain = "system"

        # Create log entry
        timestamp = datetime.now(UTC).isoformat() + "Z"
        entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "metadata": metadata or {},
            "tags": tags or []
        }

        # Determine log file path
        log_dir = os.path.join(self.logs_dir, domain)
        log_file = os.path.join(log_dir, f"{domain}_{datetime.now().strftime('%Y%m%d')}.log")

        try:
            with self.write_lock:
                # Write to file based on format
                if self.DOMAINS[domain] in ("json", "jsonl"):
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(entry) + "\n")
                else:
                    # Text format
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(f"[{timestamp}] [{level.upper()}] {message}\n")

            # Also log to console if debug mode is enabled
            if self.config_manager.get("debug_mode", False):
                print(f"[{domain.upper()}] {message}")

            return log_file
        except Exception as e:
            self.logger.error(f"Failed to write log entry: {str(e)}")
            return None

    def _setup_log_directories(self) -> None:
        """Ensure all necessary log directories exist."""
        for domain in self.DOMAINS:
            domain_path = os.path.join(self.logs_dir, domain)
            os.makedirs(domain_path, exist_ok=True)

    def _setup_file_handler(self):
        """Setup the file handler for logging."""
        try:
            log_file = os.path.join(self.logs_dir, f"dreamscape_{datetime.now().strftime('%Y%m%d')}.log")
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(file_handler)
            self.logger.info(f"Logging initialized at {self.logs_dir}")
        except Exception as e:
            self.logger.error(f"Failed to setup file handler: {str(e)}")

    def log_ai_output(
        self,
        context: str,
        input_prompt: str,
        ai_output: str,
        tags: Optional[List[str]] = None,
        result: Optional[str] = None,
        enable_reinforcement: bool = True
    ) -> Optional[str]:
        """
        Specialized method for logging AI outputs.
        Maintains compatibility with existing ai_output_logger functionality.
        """
        metadata = {
            "context": context,
            "input_prompt": input_prompt,
            "result": result
        }
        
        filepath = self.log(
            message=ai_output,
            domain="ai_output",
            metadata=metadata,
            tags=tags
        )
        
        if filepath and enable_reinforcement:
            try:
                from utils.reinforcement_trainer import process_feedback
                process_feedback({
                    "timestamp": datetime.now(UTC).isoformat() + "Z",
                    "context": context,
                    "input_prompt": input_prompt,
                    "ai_output": ai_output,
                    "tags": tags or [],
                    "result": result
                })
            except Exception as e:
                self.logger.error(f"Failed to process reinforcement feedback: {e}")
        
        return filepath

    def log_social(
        self,
        platform: str,
        event_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Specialized method for logging social interactions."""
        meta = {"platform": platform, "event_type": event_type, **(metadata or {})}
        return self.log(
            message=content,
            domain="social",
            metadata=meta,
            tags=[platform, event_type]
        )

    def log_system_event(
        self,
        event_type: str,
        message: str,
        level: str = "info",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Specialized method for logging system events."""
        return self.log(
            message=message,
            domain="system",
            level=level,
            metadata={"event_type": event_type, **(metadata or {})},
            tags=[event_type]
        )

    def get_logs(
        self,
        domain: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve logs with optional filtering.
        
        Args:
            domain: The logging domain to search
            start_time: Optional start time filter
            end_time: Optional end time filter
            filters: Optional dict of metadata filters
            
        Returns:
            List of log entries matching the criteria
        """
        logs = []
        log_dir = os.path.join(self.logs_dir, domain)
        
        if not os.path.exists(log_dir):
            self.logger.warning(f"Log directory not found: {log_dir}")
            return logs

        for log_file in sorted(Path(log_dir).glob("*.log*")):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                            
                        # Parse the log entry based on format
                        if self.DOMAINS[domain] in ("json", "jsonl"):
                            entry = json.loads(line.strip())
                        else:
                            # Parse text format
                            parts = line.strip().split("]", 2)
                            if len(parts) < 3:
                                continue
                            timestamp = parts[0][1:]
                            level = parts[1][1:]
                            message = parts[2].strip()
                            entry = {
                                "timestamp": timestamp,
                                "level": level,
                                "message": message
                            }

                        # Apply filters
                        if not self._matches_filters(entry, start_time, end_time, filters):
                            continue
                            
                        logs.append(entry)
            except Exception as e:
                self.logger.error(f"Error reading log file {log_file}: {e}")
                
        return logs

    def _matches_filters(
        self,
        entry: Dict[str, Any],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        filters: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if a log entry matches the given filters."""
        try:
            # Time filter
            entry_time = datetime.fromisoformat(entry["timestamp"].rstrip("Z"))
            if start_time and entry_time < start_time:
                return False
            if end_time and entry_time > end_time:
                return False

            # Metadata filters
            if filters:
                metadata = entry.get("metadata", {})
                for key, value in filters.items():
                    if metadata.get(key) != value:
                        return False

            return True
        except Exception:
            return False

    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an error with context.
        
        :param error: The exception to log
        :param context: Additional context information
        """
        try:
            error_msg = f"Error: {str(error)}"
            if context:
                error_msg += f"\nContext: {context}"
            self.logger.error(error_msg)
        except Exception as e:
            print(f"Failed to save error log: {str(e)}")

    def log_debug(self, message: str):
        """Log a debug message."""
        if self.config_manager.get("debug_mode", False):
            self.log(message, domain="debug", level="debug")

    def log_event(self, event_name: str, payload: dict):
        """Log a structured event."""
        self.log(
            message=f"Event: {event_name}",
            domain="system",
            metadata={"event_name": event_name, "payload": payload}
        )
