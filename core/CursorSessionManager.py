"""
CursorSessionManager.py - Handles cursor session management and recovery actions

This class manages the lifecycle of cursor sessions, including:
- Starting/ending chat sessions
- Executing recovery actions 
- Managing stall detection
- Handling task queues and isolation
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
import json
import threading

logger = logging.getLogger(__name__)

class CursorSessionManager:
    """
    Manages cursor sessions and provides recovery capabilities.
    
    Responsible for:
    - Chat session lifecycle management
    - Recovery action execution
    - Stall detection and handling
    - Task isolation and queuing
    """
    
    def __init__(self):
        """Initialize the CursorSessionManager with session state tracking."""
        self.active_sessions = {}
        self.session_history = []
        self.current_session_id = None
        self.lock = threading.RLock()
        self.task_queue = []
        self.is_running = False
        self.stall_check_interval = 30  # seconds
        self.stall_timeout = 300  # seconds
        
        # Start background thread for session management
        self._start_session_loop()
        logger.info("CursorSessionManager initialized")
    
    def _start_session_loop(self):
        """Start the background thread for session management."""
        self.is_running = True
        self.session_thread = threading.Thread(target=self._session_loop, daemon=True)
        self.session_thread.start()
        logger.info("CursorSessionManager loop started")
    
    def _session_loop(self):
        """Main loop for processing the task queue and checking for stalls."""
        while self.is_running:
            try:
                # Process the task queue
                self._process_task_queue()
                
                # Check for stalled sessions
                self._check_for_stalls()
                
                # Wait a bit before the next cycle
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in session loop: {e}")
                time.sleep(5)
    
    def _process_task_queue(self):
        """Process tasks in the queue based on priority and isolation levels."""
        with self.lock:
            if not self.task_queue:
                return
            
            # Simple processing - take the first task if no active session
            if not self.current_session_id:
                task = self.task_queue.pop(0)
                self._execute_task(task)
    
    def _execute_task(self, task):
        """Execute a task from the queue."""
        try:
            task_id = task.get("id", str(uuid.uuid4()))
            self.current_session_id = task_id
            
            # Create new session record
            session = {
                "id": task_id,
                "start_time": datetime.now().isoformat(),
                "status": "active",
                "last_activity": time.time(),
                "prompt": task.get("prompt", ""),
                "isolation_level": task.get("isolation_level", "medium"),
                "timeout": task.get("timeout", 300),
                "on_stall": task.get("on_stall"),
                "result": None
            }
            
            self.active_sessions[task_id] = session
            logger.info(f"Starting task execution for {task_id}")
            
            # Here would be the actual cursor execution logic
            # This is a stub implementation
            time.sleep(2)  # Simulate work
            result = f"Executed prompt: {task.get('prompt', '')[:50]}..."
            
            # Update session record
            session["status"] = "completed"
            session["end_time"] = datetime.now().isoformat()
            session["result"] = result
            session["last_activity"] = time.time()
            
            # Move to history
            self.session_history.append(session)
            del self.active_sessions[task_id]
            self.current_session_id = None
            
            logger.info(f"Completed task execution for {task_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing task: {e}")
            if task_id in self.active_sessions:
                self.active_sessions[task_id]["status"] = "failed"
                self.active_sessions[task_id]["error"] = str(e)
                self.active_sessions[task_id]["last_activity"] = time.time()
                
                # Move to history
                self.session_history.append(self.active_sessions[task_id])
                del self.active_sessions[task_id]
            
            self.current_session_id = None
            raise
    
    def _check_for_stalls(self):
        """Check for stalled sessions and trigger recovery if needed."""
        current_time = time.time()
        
        with self.lock:
            for session_id, session in list(self.active_sessions.items()):
                # Check if session is stalled
                if current_time - session["last_activity"] > self.stall_timeout:
                    logger.warning(f"Stalled session detected: {session_id}")
                    
                    # Execute recovery callback if provided
                    if session.get("on_stall") and callable(session["on_stall"]):
                        try:
                            logger.info(f"Executing recovery for session {session_id}")
                            recovery_result = session["on_stall"]()
                            
                            if recovery_result:
                                logger.info(f"Recovery successful for session {session_id}")
                                session["last_activity"] = current_time
                                session["recovery_attempts"] = session.get("recovery_attempts", 0) + 1
                            else:
                                logger.warning(f"Recovery failed for session {session_id}")
                                self._handle_failed_recovery(session)
                        except Exception as e:
                            logger.error(f"Error in recovery callback: {e}")
                            self._handle_failed_recovery(session)
                    else:
                        # No recovery callback, mark as failed
                        self._handle_failed_recovery(session)
    
    def _handle_failed_recovery(self, session):
        """Handle the case when recovery fails for a session."""
        session_id = session["id"]
        
        session["status"] = "failed"
        session["end_time"] = datetime.now().isoformat()
        session["error"] = "Session stalled and recovery failed"
        
        # Move to history
        self.session_history.append(session)
        del self.active_sessions[session_id]
        
        # Reset current session if this was the active one
        if self.current_session_id == session_id:
            self.current_session_id = None
    
    def start_new_chat(self):
        """Start a new chat session, closing any existing ones."""
        logger.info("Starting a new chat session")
        with self.lock:
            # Close any active session
            if self.current_session_id and self.current_session_id in self.active_sessions:
                session = self.active_sessions[self.current_session_id]
                session["status"] = "closed"
                session["end_time"] = datetime.now().isoformat()
                
                # Move to history
                self.session_history.append(session)
                del self.active_sessions[self.current_session_id]
            
            self.current_session_id = None
            return True
    
    def execute_recovery_action(self, action: str, context: Dict[str, Any]) -> bool:
        """Execute a specific recovery action."""
        logger.info(f"Executing recovery action: {action}")
        
        try:
            if action == "reload_context":
                # Simulate reloading context
                time.sleep(1)
                return True
            elif action == "reset_cursor":
                # Simulate resetting cursor
                self.start_new_chat()
                return True
            elif action == "retry_last_command":
                # Simulate retrying last command
                time.sleep(1)
                return True
            else:
                logger.warning(f"Unknown recovery action: {action}")
                return False
        except Exception as e:
            logger.error(f"Error executing recovery action {action}: {e}")
            return False
    
    def queue_prompt(self, prompt: str, isolation_level: str = "medium", on_stall: Optional[Callable] = None, timeout: int = 300):
        """Queue a prompt for execution."""
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "prompt": prompt,
            "queued_time": datetime.now().isoformat(),
            "isolation_level": isolation_level,
            "on_stall": on_stall,
            "timeout": timeout
        }
        
        with self.lock:
            self.task_queue.append(task)
        
        logger.info(f"Queued prompt with ID {task_id}")
        return task_id
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get a list of all active sessions."""
        with self.lock:
            return list(self.active_sessions.values())
    
    def get_session_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the session history, limited to the most recent N sessions."""
        with self.lock:
            return self.session_history[-limit:] if limit else self.session_history
    
    def get_task_queue(self) -> List[Dict[str, Any]]:
        """Get the current task queue."""
        with self.lock:
            return list(self.task_queue)
    
    def clear_task_queue(self) -> bool:
        """Clear the task queue."""
        with self.lock:
            self.task_queue = []
            return True
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific session."""
        with self.lock:
            # Check active sessions
            if session_id in self.active_sessions:
                return self.active_sessions[session_id]
            
            # Check session history
            for session in self.session_history:
                if session["id"] == session_id:
                    return session
            
            return None 