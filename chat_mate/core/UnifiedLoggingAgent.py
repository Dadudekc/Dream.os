import os
import json
import logging
import threading
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

from core.FileManager import FileManager
from core.PathManager import PathManager

class UnifiedLoggingAgent:
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

    def __init__(self):
        """Initialize the UnifiedLoggingAgent with necessary components."""
        self.file_manager = FileManager()
        self.write_lock = threading.Lock()
        
        # Set up the main logger
        self.logger = logging.getLogger("unified_logger")
        self.logger.setLevel(logging.INFO)
        
        # Ensure all log directories exist
        self._setup_log_directories()
        
        # Add file handler for the main log
        main_log_path = os.path.join(PathManager.get_path("logs"), "unified_log.log")
        file_handler = logging.FileHandler(main_log_path)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        )
        self.logger.addHandler(file_handler)

    def _setup_log_directories(self) -> None:
        """Ensure all necessary log directories exist."""
        for domain in self.DOMAINS:
            domain_path = os.path.join(PathManager.get_path("logs"), domain)
            os.makedirs(domain_path, exist_ok=True)

    def log(
        self,
        message: str,
        domain: str = "system",
        level: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Main logging method that handles all types of logs.
        
        Args:
            message: The main message to log
            domain: Logging domain (ai_output, social, system, etc.)
            level: Logging level (info, warning, error, critical)
            metadata: Additional structured data to include
            tags: List of tags for categorization
            
        Returns:
            Optional[str]: Path to the saved log file if successful
        """
        if domain not in self.DOMAINS:
            self.logger.warning(f"Unknown logging domain: {domain}, defaulting to 'system'")
            domain = "system"

        # Prepare the log entry
        timestamp = datetime.now(UTC).isoformat() + "Z"
        
        if self.DOMAINS[domain] in ("json", "jsonl"):
            log_entry = {
                "timestamp": timestamp,
                "level": level,
                "message": message,
                "domain": domain,
                "metadata": metadata or {},
                "tags": tags or []
            }
            content = json.dumps(log_entry, ensure_ascii=False)
            if self.DOMAINS[domain] == "jsonl":
                content += "\n"
        else:
            content = f"[{timestamp}] [{level.upper()}] {message}"
            if metadata:
                content += f" | Metadata: {json.dumps(metadata)}"
            if tags:
                content += f" | Tags: {','.join(tags)}"
            content += "\n"

        # Log to the Python logger
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message)

        # Save using FileManager
        try:
            with self.write_lock:
                return self.file_manager.save_log(
                    content=content,
                    log_type=domain
                )
        except Exception as e:
            self.logger.error(f"Failed to save log entry: {e}")
            return None

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
        log_dir = os.path.join(PathManager.get_path("logs"), domain)
        
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