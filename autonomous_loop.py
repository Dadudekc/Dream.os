#!/usr/bin/env python3
"""
Autonomous Loop for the Prompt Orchestration System.

This script watches for new tasks in the queued_tasks directory and 
executes them using the task_runner or cursor_dispatcher.
It also provides mechanisms to scrape and classify input to generate new tasks.
"""

import os
import sys
import json
import time
import shutil
import logging
import argparse
import importlib.util
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import threading
import queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('autonomous_loop.log')
    ]
)
logger = logging.getLogger('autonomous_loop')

class AutonomousLoop:
    """
    Watches for new tasks and executes them automatically.
    Also provides mechanisms to generate new tasks from various inputs.
    """
    
    def __init__(self, 
                 project_dir: str = ".",
                 queue_dir: str = "queued_tasks",
                 processed_dir: str = "processed_tasks",
                 failed_dir: str = "failed_tasks",
                 mode: str = "execute",
                 polling_interval: int = 5,
                 auto_mode: bool = False,
                 debug: bool = False):
        """
        Initialize the autonomous loop.
        
        Args:
            project_dir: Base project directory
            queue_dir: Directory to watch for new tasks
            processed_dir: Directory to move processed tasks to
            failed_dir: Directory to move failed tasks to
            mode: Execution mode (simulate, execute)
            polling_interval: Time in seconds between polling for new tasks
            auto_mode: Whether to run in automatic mode without confirmation
            debug: Whether to run in debug mode
        """
        self.project_dir = os.path.abspath(project_dir)
        self.queue_dir = os.path.join(self.project_dir, queue_dir)
        self.processed_dir = os.path.join(self.project_dir, processed_dir)
        self.failed_dir = os.path.join(self.project_dir, failed_dir)
        
        # Create directories if they don't exist
        os.makedirs(self.queue_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.failed_dir, exist_ok=True)
        
        self.mode = mode
        self.polling_interval = polling_interval
        self.auto_mode = auto_mode
        self.debug = debug
        
        # State tracking
        self.running = False
        self.paused = False
        self.task_queue = queue.Queue()
        self.active_tasks = {}
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "start_time": time.time()
        }
        
        if self.debug:
            logger.setLevel(logging.DEBUG)
        
        # Import the task_runner module
        try:
            task_runner_path = os.path.join(os.path.dirname(__file__), "task_runner.py")
            spec = importlib.util.spec_from_file_location("task_runner", task_runner_path)
            self.task_runner = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.task_runner)
            
            # Create an executor instance
            self.executor = self.task_runner.TaskExecutor(project_dir=self.project_dir)
            
        except Exception as e:
            logger.error(f"Failed to import task_runner: {str(e)}", exc_info=True)
            raise
            
        logger.info(f"Initialized AutonomousLoop with project_dir={self.project_dir}, "
                  f"queue_dir={self.queue_dir}, mode={self.mode}")
    
    def start(self):
        """Start the autonomous loop."""
        if self.running:
            logger.warning("Autonomous loop is already running")
            return
            
        self.running = True
        self.paused = False
        
        # Start the main worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        
        # Start the watcher thread
        self.watcher_thread = threading.Thread(target=self._watcher_loop)
        self.watcher_thread.daemon = True
        self.watcher_thread.start()
        
        logger.info("Autonomous loop started")
    
    def stop(self):
        """Stop the autonomous loop."""
        if not self.running:
            return
            
        logger.info("Stopping autonomous loop...")
        self.running = False
        
        # Wait for threads to complete
        if hasattr(self, 'worker_thread'):
            self.worker_thread.join(timeout=5.0)
        if hasattr(self, 'watcher_thread'):
            self.watcher_thread.join(timeout=5.0)
            
        logger.info("Autonomous loop stopped")
    
    def pause(self):
        """Pause the autonomous loop."""
        if not self.running or self.paused:
            return
            
        self.paused = True
        logger.info("Autonomous loop paused")
    
    def resume(self):
        """Resume the autonomous loop."""
        if not self.running or not self.paused:
            return
            
        self.paused = False
        logger.info("Autonomous loop resumed")
    
    def _watcher_loop(self):
        """Watch for new task files in the queue directory."""
        logger.info(f"Starting watcher loop on {self.queue_dir}")
        
        while self.running:
            if not self.paused:
                try:
                    # Get all .prompt.json files in the queue directory
                    task_files = [f for f in os.listdir(self.queue_dir) 
                               if f.endswith(".prompt.json")]
                    
                    if task_files:
                        logger.info(f"Found {len(task_files)} task files in the queue")
                        
                    for task_file in task_files:
                        task_path = os.path.join(self.queue_dir, task_file)
                        
                        # Check if we haven't already queued this task
                        if task_path not in self.active_tasks:
                            try:
                                # Load the task
                                with open(task_path, "r") as f:
                                    task = json.load(f)
                                    
                                # Add the task to the queue
                                self.task_queue.put((task_path, task))
                                self.active_tasks[task_path] = "queued"
                                logger.info(f"Queued task from {task_path}")
                                
                            except Exception as e:
                                logger.error(f"Error loading task file {task_path}: {str(e)}")
                                # Move the file to the failed directory
                                self._move_file(task_path, self.failed_dir)
                
                except Exception as e:
                    logger.error(f"Error in watcher loop: {str(e)}", exc_info=True)
            
            # Sleep before the next poll
            time.sleep(self.polling_interval)
    
    def _worker_loop(self):
        """Process tasks from the queue."""
        logger.info("Starting worker loop")
        
        while self.running:
            if not self.paused:
                try:
                    # Get a task from the queue with a timeout
                    try:
                        task_path, task = self.task_queue.get(timeout=1.0)
                    except queue.Empty:
                        continue
                        
                    logger.info(f"Processing task from {task_path}")
                    self.active_tasks[task_path] = "processing"
                    
                    # Execute the task
                    success = self._execute_task(task)
                    
                    # Update statistics
                    self.stats["total_processed"] += 1
                    if success:
                        self.stats["successful"] += 1
                        # Move the file to the processed directory
                        self._move_file(task_path, self.processed_dir)
                        self.active_tasks[task_path] = "processed"
                    else:
                        self.stats["failed"] += 1
                        # Move the file to the failed directory
                        self._move_file(task_path, self.failed_dir)
                        self.active_tasks[task_path] = "failed"
                    
                    # Mark the task as complete in the queue
                    self.task_queue.task_done()
                    
                except Exception as e:
                    logger.error(f"Error in worker loop: {str(e)}", exc_info=True)
            
            # Short sleep to prevent CPU spinning
            time.sleep(0.1)
    
    def _execute_task(self, task: Dict) -> bool:
        """
        Execute a task and return whether it was successful.
        
        Args:
            task: Task dictionary
        
        Returns:
            Whether the task was executed successfully
        """
        # Determine if this is a task for the task_runner or cursor_dispatcher
        if task.get("type") == "cursor" or task.get("is_cursor_task", False):
            return self._execute_cursor_task(task)
        else:
            return self._execute_runner_task(task)
    
    def _execute_cursor_task(self, task: Dict) -> bool:
        """Execute a task using the cursor_dispatcher."""
        try:
            # Import the cursor_dispatcher module
            cursor_dispatcher_path = os.path.join(os.path.dirname(__file__), "cursor_dispatcher.py")
            spec = importlib.util.spec_from_file_location("cursor_dispatcher", cursor_dispatcher_path)
            cursor_dispatcher = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cursor_dispatcher)
            
            # Create a dispatcher instance
            dispatcher = cursor_dispatcher.CursorDispatcher(
                project_dir=self.project_dir,
                auto_mode=self.auto_mode,
                debug=self.debug
            )
            
            # Dispatch the task
            success, result = dispatcher.dispatch_task(task)
            
            if success:
                logger.info(f"Cursor task executed successfully: {task.get('id', 'unknown')}")
                return True
            else:
                logger.error(f"Cursor task execution failed: {task.get('id', 'unknown')} - {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing cursor task: {str(e)}", exc_info=True)
            return False
    
    def _execute_runner_task(self, task: Dict) -> bool:
        """Execute a task using the task_runner."""
        try:
            # Get task object in the format expected by the task_runner
            task_runner_task = self._convert_to_task_runner_format(task)
            
            # Execute the task
            result = self.executor.execute_task(task_runner_task)
            
            if result.success:
                logger.info(f"Task executed successfully: {task.get('task_id', 'unknown')}")
                return True
            else:
                logger.error(f"Task execution failed: {task.get('task_id', 'unknown')} - {result.message}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing task: {str(e)}", exc_info=True)
            return False
    
    def _convert_to_task_runner_format(self, task: Dict) -> Dict:
        """Convert a task to the format expected by the task_runner."""
        # Map fields to task_runner format
        task_runner_task = {
            "task_id": task.get("id", task.get("task_id", str(int(time.time())))),
            "description": task.get("description", ""),
            "target": task.get("target", "CursorDispatcher"),  # Default to CursorDispatcher
            "mode": self.mode
        }
        
        # Copy all other fields
        for key, value in task.items():
            if key not in ["id", "task_id", "description", "target"]:
                task_runner_task[key] = value
                
        return task_runner_task
    
    def _move_file(self, src_path: str, dest_dir: str) -> None:
        """Move a file to a destination directory with timestamp."""
        try:
            # Get the base filename
            basename = os.path.basename(src_path)
            
            # Add a timestamp to make the filename unique
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(basename)
            new_name = f"{name}_{timestamp}{ext}"
            
            # Create the destination path
            dest_path = os.path.join(dest_dir, new_name)
            
            # Move the file
            shutil.move(src_path, dest_path)
            logger.debug(f"Moved {src_path} to {dest_path}")
            
            # Remove from active tasks if it's there
            if src_path in self.active_tasks:
                del self.active_tasks[src_path]
                
        except Exception as e:
            logger.error(f"Error moving file {src_path}: {str(e)}")
    
    def generate_task_from_web(self, url: str, task_type: str) -> Optional[str]:
        """
        Generate a task from a web page.
        
        Args:
            url: URL to scrape
            task_type: Type of task to generate
            
        Returns:
            Path to the generated task file, or None if failed
        """
        # This would scrape the website and generate a task based on the content
        # For now, we'll just create a simple template task
        task = {
            "id": f"web_{int(time.time())}",
            "description": f"Task generated from {url}",
            "type": "cursor",
            "is_cursor_task": True,
            "template_name": "web/web_analysis_template",
            "params": {
                "url": url,
                "task_type": task_type,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            "target_output": "web_analysis"
        }
        
        # Save the task to the queue directory
        task_filename = f"task_web_{int(time.time())}.prompt.json"
        task_path = os.path.join(self.queue_dir, task_filename)
        
        try:
            with open(task_path, "w") as f:
                json.dump(task, f, indent=2)
            
            logger.info(f"Generated web task at {task_path}")
            return task_path
            
        except Exception as e:
            logger.error(f"Error generating web task: {str(e)}")
            return None
    
    def generate_task_from_project(self, project_path: str, task_type: str) -> Optional[str]:
        """
        Generate a task from a project directory.
        
        Args:
            project_path: Path to the project to analyze
            task_type: Type of task to generate
            
        Returns:
            Path to the generated task file, or None if failed
        """
        # This would analyze the project and generate a task based on the content
        # For now, we'll just create a simple template task
        task = {
            "id": f"project_{int(time.time())}",
            "description": f"Task generated from project {project_path}",
            "type": "cursor",
            "is_cursor_task": True,
            "template_name": "project/project_analysis_template",
            "params": {
                "project_path": project_path,
                "task_type": task_type,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            "target_output": "project_analysis"
        }
        
        # Save the task to the queue directory
        task_filename = f"task_project_{int(time.time())}.prompt.json"
        task_path = os.path.join(self.queue_dir, task_filename)
        
        try:
            with open(task_path, "w") as f:
                json.dump(task, f, indent=2)
            
            logger.info(f"Generated project task at {task_path}")
            return task_path
            
        except Exception as e:
            logger.error(f"Error generating project task: {str(e)}")
            return None
    
    def generate_task_from_file(self, file_path: str, task_type: str) -> Optional[str]:
        """
        Generate a task from a file.
        
        Args:
            file_path: Path to the file to analyze
            task_type: Type of task to generate
            
        Returns:
            Path to the generated task file, or None if failed
        """
        # This would analyze the file and generate a task based on the content
        # For now, we'll just create a simple template task
        task = {
            "id": f"file_{int(time.time())}",
            "description": f"Task generated from file {file_path}",
            "type": "cursor",
            "is_cursor_task": True,
            "template_name": "file/file_analysis_template",
            "params": {
                "file_path": file_path,
                "task_type": task_type,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            "target_output": "file_analysis"
        }
        
        # Save the task to the queue directory
        task_filename = f"task_file_{int(time.time())}.prompt.json"
        task_path = os.path.join(self.queue_dir, task_filename)
        
        try:
            with open(task_path, "w") as f:
                json.dump(task, f, indent=2)
            
            logger.info(f"Generated file task at {task_path}")
            return task_path
            
        except Exception as e:
            logger.error(f"Error generating file task: {str(e)}")
            return None
    
    def get_stats(self) -> Dict:
        """Get statistics about the autonomous loop."""
        current_time = time.time()
        runtime = current_time - self.stats["start_time"]
        
        stats = {
            **self.stats,
            "runtime_seconds": runtime,
            "runtime_formatted": self._format_time(runtime),
            "tasks_per_hour": (self.stats["total_processed"] / runtime) * 3600 if runtime > 0 else 0,
            "success_rate": (self.stats["successful"] / self.stats["total_processed"]) * 100 if self.stats["total_processed"] > 0 else 0,
            "queue_size": self.task_queue.qsize(),
            "active_tasks": len(self.active_tasks)
        }
        
        return stats
    
    def _format_time(self, seconds: float) -> str:
        """Format a time in seconds to a human-readable string."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def main():
    """Main entry point for the autonomous loop."""
    parser = argparse.ArgumentParser(description="Autonomous loop for the Prompt Orchestration System")
    
    parser.add_argument("--project-dir", "-p", type=str, default=".",
                      help="Project directory")
    parser.add_argument("--queue-dir", "-q", type=str, default="queued_tasks",
                      help="Directory to watch for new tasks")
    parser.add_argument("--mode", "-m", type=str, choices=["simulate", "execute"],
                      default="simulate", help="Execution mode")
    parser.add_argument("--interval", "-i", type=int, default=5,
                      help="Polling interval in seconds")
    parser.add_argument("--auto", "-a", action="store_true",
                      help="Run in automatic mode without confirmation")
    parser.add_argument("--debug", action="store_true",
                      help="Run in debug mode")
    
    # Optional: generate a task
    parser.add_argument("--generate-web", type=str,
                      help="Generate a task from a web page")
    parser.add_argument("--generate-project", type=str,
                      help="Generate a task from a project directory")
    parser.add_argument("--generate-file", type=str,
                      help="Generate a task from a file")
    parser.add_argument("--task-type", type=str, default="analysis",
                      help="Type of task to generate")
    
    parser.add_argument("--no-loop", action="store_true",
                      help="Don't start the loop, just generate tasks")
    
    args = parser.parse_args()
    
    # Create the autonomous loop
    loop = AutonomousLoop(
        project_dir=args.project_dir,
        queue_dir=args.queue_dir,
        mode=args.mode,
        polling_interval=args.interval,
        auto_mode=args.auto,
        debug=args.debug
    )
    
    # Generate tasks if requested
    if args.generate_web:
        loop.generate_task_from_web(args.generate_web, args.task_type)
    
    if args.generate_project:
        loop.generate_task_from_project(args.generate_project, args.task_type)
    
    if args.generate_file:
        loop.generate_task_from_file(args.generate_file, args.task_type)
    
    # Don't start the loop if --no-loop is specified
    if args.no_loop:
        logger.info("Tasks generated, not starting the loop (--no-loop specified)")
        return
    
    try:
        # Start the autonomous loop
        loop.start()
        
        # Keep the main thread alive with a message every minute
        while True:
            time.sleep(60)
            stats = loop.get_stats()
            logger.info(f"Autonomous loop running for {stats['runtime_formatted']}, "
                       f"processed {stats['total_processed']} tasks "
                       f"({stats['success_rate']:.1f}% success rate), "
                       f"{stats['queue_size']} in queue")
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping...")
    finally:
        loop.stop()
        
        # Print final stats
        stats = loop.get_stats()
        logger.info(f"Autonomous loop stopped after {stats['runtime_formatted']}")
        logger.info(f"Processed {stats['total_processed']} tasks: "
                  f"{stats['successful']} successful, {stats['failed']} failed "
                  f"({stats['success_rate']:.1f}% success rate)")


if __name__ == "__main__":
    main() 