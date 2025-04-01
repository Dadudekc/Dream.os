#!/usr/bin/env python3
"""
Task Watcher Script
Monitors the Cursor queued tasks directory for new tasks and
processes auto-execution tasks without requiring manual approval.
"""

import json
import os
import time
import logging
import sys
import subprocess
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('task_watcher.log')
    ]
)

logger = logging.getLogger('task_watcher')

class TaskWatcher:
    """Watches for Cursor tasks and manages auto-execution."""
    
    def __init__(self, 
                 queued_dir: str = ".cursor/queued_tasks",
                 executed_dir: str = ".cursor/executed_tasks",
                 memory_file: str = "memory/task_history.json",
                 check_interval: int = 5):
        """
        Initialize the TaskWatcher.
        
        Args:
            queued_dir: Directory for queued tasks
            executed_dir: Directory for executed/completed tasks
            memory_file: File for storing task history
            check_interval: Time in seconds between checks for new tasks
        """
        self.queued_dir = Path(queued_dir)
        self.executed_dir = Path(executed_dir)
        self.memory_file = Path(memory_file)
        self.check_interval = check_interval
        
        # Ensure directories exist
        self.queued_dir.mkdir(parents=True, exist_ok=True)
        self.executed_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize memory file if it doesn't exist
        if not self.memory_file.exists():
            with open(self.memory_file, 'w') as f:
                json.dump({"tasks": []}, f, indent=2)
                
        logger.info(f"TaskWatcher initialized with queued_dir={queued_dir}, check_interval={check_interval}s")
    
    def run(self):
        """Start the watcher loop."""
        logger.info("TaskWatcher started. Monitoring for new tasks...")
        
        try:
            while True:
                self.check_for_tasks()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("TaskWatcher stopped by user")
            return
    
    def check_for_tasks(self):
        """Check for new tasks in the queued_dir."""
        try:
            # Find auto-execute tasks
            auto_execute_tasks = []
            task_files = list(self.queued_dir.glob("*.json"))
            
            if not task_files:
                return
                
            logger.debug(f"Found {len(task_files)} task files")
            
            for task_file in task_files:
                try:
                    with open(task_file, 'r') as f:
                        task = json.load(f)
                        
                    if task.get("auto_execute", False):
                        auto_execute_tasks.append((task_file, task))
                except Exception as e:
                    logger.error(f"Error reading task file {task_file}: {e}")
            
            if not auto_execute_tasks:
                logger.debug("No auto-execute tasks found")
                return
                
            logger.info(f"Found {len(auto_execute_tasks)} auto-execute tasks")
            
            # Process auto-execute tasks
            for task_file, task in auto_execute_tasks:
                self.process_task(task_file, task)
                
        except Exception as e:
            logger.error(f"Error checking for tasks: {e}")
    
    def process_task(self, task_file: Path, task: Dict[str, Any]):
        """
        Process an auto-execute task.
        
        Args:
            task_file: Path to the task file
            task: Task data dictionary
        """
        task_id = task.get("id", "unknown")
        logger.info(f"Processing auto-execute task {task_id}")
        
        try:
            # Mark task as running
            task["status"] = "running"
            with open(task_file, 'w') as f:
                json.dump(task, f, indent=2)
            
            self.update_task_in_memory(task)
            
            # Extract task details
            rendered_prompt = task.get("rendered_prompt", "")
            target_output = task.get("target_output", "output.py")
            
            # Create target directory if needed
            target_path = Path(target_output)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the rendered prompt to the target file
            with open(target_output, 'w') as f:
                f.write(rendered_prompt)
                
            logger.info(f"Task {task_id} executed successfully, output written to {target_output}")
            
            # Update task status
            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat()
            task["result"] = {
                "success": True,
                "output_file": target_output
            }
            
            # Move to executed directory
            executed_file = self.executed_dir / task_file.name
            with open(executed_file, 'w') as f:
                json.dump(task, f, indent=2)
                
            # Remove from queued directory
            task_file.unlink()
            
            # Update memory
            self.update_task_in_memory(task)
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            
            # Mark as failed
            task["status"] = "failed"
            task["completed_at"] = datetime.now().isoformat()
            task["result"] = {
                "success": False,
                "error": str(e)
            }
            
            # Move to executed directory
            executed_file = self.executed_dir / task_file.name
            with open(executed_file, 'w') as f:
                json.dump(task, f, indent=2)
                
            # Remove from queued directory
            if task_file.exists():
                task_file.unlink()
                
            # Update memory
            self.update_task_in_memory(task)
    
    def update_task_in_memory(self, task: Dict[str, Any]):
        """
        Update a task in the memory file.
        
        Args:
            task: Updated task data
        """
        try:
            # Read memory file
            with open(self.memory_file, 'r') as f:
                memory = json.load(f)
            
            # Find and update the task
            task_id = task["id"]
            for i, t in enumerate(memory.get("tasks", [])):
                if t.get("id") == task_id:
                    memory["tasks"][i] = task
                    break
            else:
                # Task not found, add it
                memory.setdefault("tasks", []).append(task)
            
            # Write back to file
            with open(self.memory_file, 'w') as f:
                json.dump(memory, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error updating task in memory: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Task Watcher for Cursor tasks")
    parser.add_argument("--queued-dir", default=".cursor/queued_tasks", help="Directory for queued tasks")
    parser.add_argument("--executed-dir", default=".cursor/executed_tasks", help="Directory for executed tasks")
    parser.add_argument("--memory-file", default="memory/task_history.json", help="File for task history")
    parser.add_argument("--interval", type=int, default=5, help="Check interval in seconds")
    
    args = parser.parse_args()
    
    watcher = TaskWatcher(
        queued_dir=args.queued_dir,
        executed_dir=args.executed_dir,
        memory_file=args.memory_file,
        check_interval=args.interval
    )
    
    watcher.run() 