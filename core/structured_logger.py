#!/usr/bin/env python3
"""
StructuredLogger - JSONL-formatted logging for LLM and dashboard consumption
===========================================================================

Replaces traditional text logging with structured JSON logs that can be:
1. Easily parsed by dashboards and monitoring systems
2. Fed back into LLMs for analysis and troubleshooting
3. Queried and filtered efficiently

Each log entry includes consistent metadata like timestamp, level, event, 
task_id, and custom fields relevant to the event.
"""

import os
import json
import time
import logging
import threading
from typing import Dict, Any, Optional, Union, List
from datetime import datetime

# Configure standard logging
logger = logging.getLogger(__name__)

class StructuredLogger:
    """
    Structured logger that outputs JSONL-formatted logs with consistent metadata.
    
    Features:
    - JSONL output format (one JSON object per line)
    - Consistent metadata for all log entries (timestamp, level, etc.)
    - Event-based logging for easy filtering and analysis
    - Thread-safe logging to prevent interleaved output
    - Automatic log rotation to prevent huge files
    """
    
    def __init__(self, 
                 log_file_path: str = None,
                 app_name: str = "cursor",
                 max_file_size_mb: int = 10,
                 max_files: int = 5,
                 console_logging: bool = True):
        """
        Initialize the structured logger.
        
        Args:
            log_file_path: Path to the log file (default: app_name.jsonl)
            app_name: Name of the application for the logs
            max_file_size_mb: Maximum log file size in MB before rotation
            max_files: Maximum number of rotated log files to keep
            console_logging: Whether to also log to console
        """
        self.app_name = app_name
        self.log_file_path = log_file_path or f"{app_name}.jsonl"
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.max_files = max_files
        self.console_logging = console_logging
        self._lock = threading.RLock()
        
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        logger.info(f"StructuredLogger initialized with log file: {self.log_file_path}")
    
    def log(self, 
            event: str, 
            level: str = "info", 
            task_id: Optional[str] = None,
            duration_ms: Optional[float] = None,
            **kwargs) -> Dict[str, Any]:
        """
        Log an event with structured metadata.
        
        Args:
            event: Name of the event (e.g., 'task_started', 'task_completed')
            level: Log level (debug, info, warning, error, critical)
            task_id: ID of the associated task, if any
            duration_ms: Duration of the event in milliseconds, if applicable
            **kwargs: Additional fields to include in the log entry
            
        Returns:
            The log entry as a dictionary
        """
        with self._lock:
            # Prepare log entry
            entry = {
                "timestamp": datetime.now().isoformat(),
                "app": self.app_name,
                "level": level,
                "event": event
            }
            
            # Add task_id if provided
            if task_id:
                entry["task_id"] = task_id
                
            # Add duration if provided
            if duration_ms is not None:
                entry["duration_ms"] = duration_ms
                
            # Add additional fields
            entry.update(kwargs)
            
            # Write to log file
            self._write_log(entry)
            
            # Also log to console if enabled
            if self.console_logging:
                self._log_to_console(entry)
            
            return entry
    
    def task_started(self, 
                     task_id: str, 
                     task_type: str, 
                     priority: str = "medium",
                     **kwargs) -> Dict[str, Any]:
        """
        Log a task started event.
        
        Args:
            task_id: ID of the task
            task_type: Type of the task
            priority: Priority of the task
            **kwargs: Additional fields to include
            
        Returns:
            The log entry
        """
        return self.log(
            event="task_started",
            level="info",
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            **kwargs
        )
    
    def task_completed(self, 
                       task_id: str, 
                       success: bool = True, 
                       duration_ms: Optional[float] = None,
                       **kwargs) -> Dict[str, Any]:
        """
        Log a task completed event.
        
        Args:
            task_id: ID of the task
            success: Whether the task completed successfully
            duration_ms: Duration of the task in milliseconds
            **kwargs: Additional fields to include
            
        Returns:
            The log entry
        """
        level = "info" if success else "warning"
        return self.log(
            event="task_completed",
            level=level,
            task_id=task_id,
            success=success,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def task_failed(self, 
                    task_id: str, 
                    error: str,
                    error_type: Optional[str] = None,
                    duration_ms: Optional[float] = None,
                    **kwargs) -> Dict[str, Any]:
        """
        Log a task failed event.
        
        Args:
            task_id: ID of the task
            error: Error message
            error_type: Type of error
            duration_ms: Duration of the task in milliseconds
            **kwargs: Additional fields to include
            
        Returns:
            The log entry
        """
        return self.log(
            event="task_failed",
            level="error",
            task_id=task_id,
            error=error,
            error_type=error_type,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def model_request(self, 
                      task_id: Optional[str], 
                      model: str,
                      prompt_tokens: int,
                      **kwargs) -> Dict[str, Any]:
        """
        Log a model request event.
        
        Args:
            task_id: ID of the associated task, if any
            model: Name of the model
            prompt_tokens: Number of tokens in the prompt
            **kwargs: Additional fields to include
            
        Returns:
            The log entry
        """
        return self.log(
            event="model_request",
            level="info",
            task_id=task_id,
            model=model,
            prompt_tokens=prompt_tokens,
            **kwargs
        )
    
    def model_response(self, 
                       task_id: Optional[str], 
                       model: str,
                       completion_tokens: int,
                       success: bool = True,
                       duration_ms: Optional[float] = None,
                       **kwargs) -> Dict[str, Any]:
        """
        Log a model response event.
        
        Args:
            task_id: ID of the associated task, if any
            model: Name of the model
            completion_tokens: Number of tokens in the response
            success: Whether the request was successful
            duration_ms: Duration of the request in milliseconds
            **kwargs: Additional fields to include
            
        Returns:
            The log entry
        """
        level = "info" if success else "error"
        return self.log(
            event="model_response",
            level=level,
            task_id=task_id,
            model=model,
            completion_tokens=completion_tokens,
            success=success,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def file_modified(self, 
                      task_id: Optional[str], 
                      file_path: str,
                      action: str,
                      lines_changed: Optional[int] = None,
                      **kwargs) -> Dict[str, Any]:
        """
        Log a file modification event.
        
        Args:
            task_id: ID of the associated task, if any
            file_path: Path to the modified file
            action: Type of modification (created, updated, deleted)
            lines_changed: Number of lines changed
            **kwargs: Additional fields to include
            
        Returns:
            The log entry
        """
        return self.log(
            event="file_modified",
            level="info",
            task_id=task_id,
            file_path=file_path,
            action=action,
            lines_changed=lines_changed,
            **kwargs
        )
    
    def test_result(self, 
                   task_id: Optional[str], 
                   test_file: str,
                   passed: int,
                   failed: int,
                   skipped: int,
                   coverage: Optional[float] = None,
                   **kwargs) -> Dict[str, Any]:
        """
        Log a test result event.
        
        Args:
            task_id: ID of the associated task, if any
            test_file: Path to the test file
            passed: Number of passed tests
            failed: Number of failed tests
            skipped: Number of skipped tests
            coverage: Test coverage percentage
            **kwargs: Additional fields to include
            
        Returns:
            The log entry
        """
        level = "info" if failed == 0 else "warning"
        return self.log(
            event="test_result",
            level=level,
            task_id=task_id,
            test_file=test_file,
            passed=passed,
            failed=failed,
            skipped=skipped,
            coverage=coverage,
            **kwargs
        )
    
    def metric(self, 
              name: str, 
              value: Union[int, float, str, bool],
              task_id: Optional[str] = None,
              **kwargs) -> Dict[str, Any]:
        """
        Log a metric event.
        
        Args:
            name: Name of the metric
            value: Value of the metric
            task_id: ID of the associated task, if any
            **kwargs: Additional fields to include
            
        Returns:
            The log entry
        """
        return self.log(
            event="metric",
            level="info",
            task_id=task_id,
            metric_name=name,
            metric_value=value,
            **kwargs
        )
    
    def error(self, 
             message: str, 
             error_type: Optional[str] = None,
             task_id: Optional[str] = None,
             **kwargs) -> Dict[str, Any]:
        """
        Log an error event.
        
        Args:
            message: Error message
            error_type: Type of error
            task_id: ID of the associated task, if any
            **kwargs: Additional fields to include
            
        Returns:
            The log entry
        """
        return self.log(
            event="error",
            level="error",
            task_id=task_id,
            message=message,
            error_type=error_type,
            **kwargs
        )
    
    def warning(self, 
               message: str, 
               task_id: Optional[str] = None,
               **kwargs) -> Dict[str, Any]:
        """
        Log a warning event.
        
        Args:
            message: Warning message
            task_id: ID of the associated task, if any
            **kwargs: Additional fields to include
            
        Returns:
            The log entry
        """
        return self.log(
            event="warning",
            level="warning",
            task_id=task_id,
            message=message,
            **kwargs
        )
    
    def info(self, 
            message: str, 
            task_id: Optional[str] = None,
            **kwargs) -> Dict[str, Any]:
        """
        Log an info event.
        
        Args:
            message: Info message
            task_id: ID of the associated task, if any
            **kwargs: Additional fields to include
            
        Returns:
            The log entry
        """
        return self.log(
            event="info",
            level="info",
            task_id=task_id,
            message=message,
            **kwargs
        )
    
    def debug(self, 
             message: str, 
             task_id: Optional[str] = None,
             **kwargs) -> Dict[str, Any]:
        """
        Log a debug event.
        
        Args:
            message: Debug message
            task_id: ID of the associated task, if any
            **kwargs: Additional fields to include
            
        Returns:
            The log entry
        """
        return self.log(
            event="debug",
            level="debug",
            task_id=task_id,
            message=message,
            **kwargs
        )
    
    def _write_log(self, entry: Dict[str, Any]) -> None:
        """
        Write a log entry to the log file.
        
        Args:
            entry: Log entry to write
        """
        # Check if log file needs rotation
        self._rotate_logs_if_needed()
        
        # Write log entry
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write to log file: {e}")
    
    def _log_to_console(self, entry: Dict[str, Any]) -> None:
        """
        Log an entry to the console using standard logging.
        
        Args:
            entry: Log entry to log
        """
        # Map level to logging level
        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
        }
        level = level_map.get(entry.get("level", "info"), logging.INFO)
        
        # Format message
        event = entry.get("event", "")
        task_id = entry.get("task_id", "")
        message = entry.get("message", "")
        
        if not message:
            if "error" in entry:
                message = entry["error"]
            elif event == "task_completed":
                message = f"Task {task_id} completed"
                if not entry.get("success", True):
                    message += " with errors"
            elif event == "task_failed":
                message = f"Task {task_id} failed: {entry.get('error', '')}"
            else:
                # For other events, create a string representation
                message = f"{event}: " + ", ".join(
                    f"{k}={v}" for k, v in entry.items()
                    if k not in ["timestamp", "app", "level", "event"]
                )
        
        # Format with task ID if available
        if task_id:
            message = f"[{task_id}] {message}"
        
        # Log to console
        logger.log(level, message)
    
    def _rotate_logs_if_needed(self) -> None:
        """
        Rotate log files if the current log file exceeds the maximum size.
        """
        # Check if the log file exists and exceeds the maximum size
        if not os.path.exists(self.log_file_path):
            return
        
        if os.path.getsize(self.log_file_path) < self.max_file_size_bytes:
            return
        
        # Rotate log files
        for i in range(self.max_files - 1, 0, -1):
            old_log = f"{self.log_file_path}.{i}"
            new_log = f"{self.log_file_path}.{i+1}"
            
            if os.path.exists(old_log):
                if i == self.max_files - 1:
                    # Delete the oldest log file
                    try:
                        os.remove(old_log)
                    except Exception as e:
                        logger.error(f"Failed to delete old log file: {e}")
                else:
                    # Rename the log file
                    try:
                        os.rename(old_log, new_log)
                    except Exception as e:
                        logger.error(f"Failed to rename log file: {e}")
        
        # Rename the current log file
        try:
            os.rename(self.log_file_path, f"{self.log_file_path}.1")
        except Exception as e:
            logger.error(f"Failed to rename current log file: {e}")
    
    def get_logs(self, 
                filter_event: Optional[str] = None,
                filter_level: Optional[str] = None,
                filter_task_id: Optional[str] = None,
                limit: int = 100,
                start_timestamp: Optional[str] = None,
                end_timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get logs from the log file with optional filtering.
        
        Args:
            filter_event: Filter by event name
            filter_level: Filter by log level
            filter_task_id: Filter by task ID
            limit: Maximum number of logs to return
            start_timestamp: Start timestamp (ISO format)
            end_timestamp: End timestamp (ISO format)
            
        Returns:
            List of log entries
        """
        logs = []
        try:
            with open(self.log_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        
                        # Apply filters
                        if filter_event and entry.get("event") != filter_event:
                            continue
                        
                        if filter_level and entry.get("level") != filter_level:
                            continue
                        
                        if filter_task_id and entry.get("task_id") != filter_task_id:
                            continue
                        
                        if start_timestamp and entry.get("timestamp", "") < start_timestamp:
                            continue
                        
                        if end_timestamp and entry.get("timestamp", "") > end_timestamp:
                            continue
                        
                        logs.append(entry)
                        
                        # Check limit
                        if len(logs) >= limit:
                            break
                    except:
                        # Skip invalid lines
                        continue
        except Exception as e:
            logger.error(f"Failed to read log file: {e}")
        
        return logs
    
    def get_task_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get all logs for a specific task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            List of log entries for the task
        """
        return self.get_logs(filter_task_id=task_id, limit=1000)
    
    def get_latest_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the latest error logs.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List of error log entries
        """
        return self.get_logs(filter_level="error", limit=limit) 