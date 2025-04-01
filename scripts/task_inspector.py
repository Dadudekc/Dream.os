#!/usr/bin/env python3
"""
Task Inspector

A utility script to inspect, debug, and manage Cursor tasks.
Provides a command-line interface for viewing and manipulating tasks.
"""

import os
import sys
import json
import argparse
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

def load_tasks(queued_dir: str = ".cursor/queued_tasks", 
              executed_dir: str = ".cursor/executed_tasks",
              memory_file: str = "memory/task_history.json") -> Dict[str, List[Dict[str, Any]]]:
    """
    Load tasks from queued, executed directories and memory file.
    
    Args:
        queued_dir: Directory for queued tasks
        executed_dir: Directory for executed tasks
        memory_file: File containing task history
        
    Returns:
        Dictionary with lists of tasks from each source
    """
    tasks = {
        "queued": [],
        "executed": [],
        "memory": []
    }
    
    # Load queued tasks
    queued_path = Path(queued_dir)
    if queued_path.exists():
        for file in queued_path.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    task = json.load(f)
                    task["file_path"] = str(file)
                    tasks["queued"].append(task)
            except Exception as e:
                print(f"Error loading queued task {file}: {e}")
    
    # Load executed tasks
    executed_path = Path(executed_dir)
    if executed_path.exists():
        for file in executed_path.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    task = json.load(f)
                    task["file_path"] = str(file)
                    tasks["executed"].append(task)
            except Exception as e:
                print(f"Error loading executed task {file}: {e}")
    
    # Load memory tasks
    memory_path = Path(memory_file)
    if memory_path.exists():
        try:
            with open(memory_path, 'r') as f:
                memory = json.load(f)
                tasks["memory"] = memory.get("tasks", [])
        except Exception as e:
            print(f"Error loading memory file: {e}")
    
    return tasks

def display_task_summary(tasks: Dict[str, List[Dict[str, Any]]]):
    """
    Display a summary of all tasks.
    
    Args:
        tasks: Dictionary with lists of tasks
    """
    print("\n=== Task Summary ===")
    print(f"Queued tasks: {len(tasks['queued'])}")
    print(f"Executed tasks: {len(tasks['executed'])}")
    print(f"Memory tasks: {len(tasks['memory'])}")
    print()
    
    # Count by status
    status_counts = {}
    for task in tasks["memory"]:
        status = task.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("Status counts:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
    print()
    
    # Count by template
    template_counts = {}
    for task in tasks["memory"]:
        template = task.get("template_name", "unknown")
        template_counts[template] = template_counts.get(template, 0) + 1
    
    print("Template counts:")
    for template, count in sorted(template_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {template}: {count}")
    print()
    
    # Recent tasks
    print("Recent tasks:")
    recent_tasks = sorted(
        tasks["memory"], 
        key=lambda x: x.get("timestamp", ""), 
        reverse=True
    )[:5]
    
    for i, task in enumerate(recent_tasks):
        id_short = task.get("id", "")[:8]
        template = task.get("template_name", "unknown")
        status = task.get("status", "unknown")
        timestamp = task.get("timestamp", "")
        print(f"  {i+1}. [{status}] {template} ({id_short}...) - {timestamp}")
    
    print()

def display_task_details(task_id: str, tasks: Dict[str, List[Dict[str, Any]]]):
    """
    Display detailed information about a specific task.
    
    Args:
        task_id: ID of the task to display
        tasks: Dictionary with lists of tasks
    """
    # Find the task in all sources
    task = None
    source = None
    
    # First check queued tasks
    for t in tasks["queued"]:
        if t.get("id") == task_id:
            task = t
            source = "queued"
            break
    
    # Then check executed tasks
    if not task:
        for t in tasks["executed"]:
            if t.get("id") == task_id:
                task = t
                source = "executed"
                break
    
    # Finally check memory tasks
    if not task:
        for t in tasks["memory"]:
            if t.get("id") == task_id:
                task = t
                source = "memory"
                break
    
    if not task:
        print(f"Task with ID {task_id} not found.")
        return
    
    print(f"\n=== Task Details ({source}) ===")
    print(f"ID: {task.get('id', 'unknown')}")
    print(f"Template: {task.get('template_name', 'unknown')}")
    print(f"Status: {task.get('status', 'unknown')}")
    print(f"Target Output: {task.get('target_output', 'unknown')}")
    print(f"Timestamp: {task.get('timestamp', 'unknown')}")
    
    if "completed_at" in task:
        print(f"Completed At: {task.get('completed_at', 'unknown')}")
    
    if "auto_execute" in task:
        print(f"Auto-execute: {task.get('auto_execute', False)}")
    
    if "file_path" in task:
        print(f"File Path: {task.get('file_path', 'unknown')}")
    
    # Show context
    if "context" in task:
        print("\nContext:")
        context = task.get("context", {})
        print(json.dumps(context, indent=2))
    
    # Show rendered prompt (truncated if too long)
    if "rendered_prompt" in task:
        print("\nRendered Prompt:")
        prompt = task.get("rendered_prompt", "")
        if len(prompt) > 500:
            print(prompt[:500] + "...\n[truncated, use --output to save full content]")
        else:
            print(prompt)
    
    # Show result if available
    if "result" in task and task["result"]:
        print("\nResult:")
        result = task.get("result", {})
        print(json.dumps(result, indent=2))
    
    print()

def save_task_output(task_id: str, output_file: str, tasks: Dict[str, List[Dict[str, Any]]]):
    """
    Save a task's rendered prompt to a file.
    
    Args:
        task_id: ID of the task to save
        output_file: File to save the prompt to
        tasks: Dictionary with lists of tasks
    """
    # Find the task in all sources
    task = None
    
    # Check all sources
    for source in ["queued", "executed", "memory"]:
        for t in tasks[source]:
            if t.get("id") == task_id:
                task = t
                break
        if task:
            break
    
    if not task:
        print(f"Task with ID {task_id} not found.")
        return
    
    if "rendered_prompt" not in task:
        print(f"Task {task_id} does not have a rendered prompt.")
        return
    
    # Save to file
    try:
        with open(output_file, 'w') as f:
            f.write(task.get("rendered_prompt", ""))
        print(f"Saved task prompt to {output_file}")
    except Exception as e:
        print(f"Error saving task prompt: {e}")

def delete_task(task_id: str, queued_dir: str = ".cursor/queued_tasks", 
               executed_dir: str = ".cursor/executed_tasks",
               memory_file: str = "memory/task_history.json") -> bool:
    """
    Delete a task from all locations.
    
    Args:
        task_id: ID of the task to delete
        queued_dir: Directory for queued tasks
        executed_dir: Directory for executed tasks
        memory_file: File containing task history
        
    Returns:
        True if task was deleted, False otherwise
    """
    deleted = False
    
    # Delete from queued directory
    queued_path = Path(queued_dir)
    if queued_path.exists():
        for file in queued_path.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    task = json.load(f)
                if task.get("id") == task_id:
                    os.remove(file)
                    print(f"Deleted queued task file: {file}")
                    deleted = True
            except Exception as e:
                print(f"Error processing queued task {file}: {e}")
    
    # Delete from executed directory
    executed_path = Path(executed_dir)
    if executed_path.exists():
        for file in executed_path.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    task = json.load(f)
                if task.get("id") == task_id:
                    os.remove(file)
                    print(f"Deleted executed task file: {file}")
                    deleted = True
            except Exception as e:
                print(f"Error processing executed task {file}: {e}")
    
    # Delete from memory file
    memory_path = Path(memory_file)
    if memory_path.exists():
        try:
            with open(memory_path, 'r') as f:
                memory = json.load(f)
            
            # Remove task from memory
            original_count = len(memory.get("tasks", []))
            memory["tasks"] = [t for t in memory.get("tasks", []) if t.get("id") != task_id]
            
            if len(memory.get("tasks", [])) < original_count:
                # Task was removed, save memory file
                with open(memory_path, 'w') as f:
                    json.dump(memory, f, indent=2)
                print(f"Deleted task from memory file")
                deleted = True
        except Exception as e:
            print(f"Error updating memory file: {e}")
    
    return deleted

def repair_memory_file(memory_file: str = "memory/task_history.json"):
    """
    Repair the memory file by removing duplicates and fixing inconsistencies.
    
    Args:
        memory_file: File containing task history
    """
    memory_path = Path(memory_file)
    if not memory_path.exists():
        print(f"Memory file {memory_file} does not exist.")
        return
    
    try:
        with open(memory_path, 'r') as f:
            memory = json.load(f)
        
        # Get original tasks
        original_tasks = memory.get("tasks", [])
        original_count = len(original_tasks)
        
        # Remove duplicates by ID
        unique_tasks = {}
        for task in original_tasks:
            if "id" in task:
                unique_tasks[task["id"]] = task
        
        # Get the unique tasks list
        tasks = list(unique_tasks.values())
        
        # Sort by timestamp
        tasks.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Update memory
        memory["tasks"] = tasks
        
        # Save memory file
        with open(memory_path, 'w') as f:
            json.dump(memory, f, indent=2)
        
        print(f"Memory file repaired. Removed {original_count - len(tasks)} duplicates.")
        
    except Exception as e:
        print(f"Error repairing memory file: {e}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Task Inspector Utility")
    
    # Command selection
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--summary", action="store_true", help="Display task summary")
    group.add_argument("--show", metavar="TASK_ID", help="Show details for a specific task")
    group.add_argument("--delete", metavar="TASK_ID", help="Delete a specific task")
    group.add_argument("--repair", action="store_true", help="Repair the memory file")
    
    # Additional options
    parser.add_argument("--output", metavar="FILE", help="Save task prompt to a file")
    
    # Path configuration
    parser.add_argument("--queued-dir", default=".cursor/queued_tasks", help="Directory for queued tasks")
    parser.add_argument("--executed-dir", default=".cursor/executed_tasks", help="Directory for executed tasks")
    parser.add_argument("--memory-file", default="memory/task_history.json", help="File for task history")
    
    args = parser.parse_args()
    
    # Load tasks
    if args.summary or args.show:
        tasks = load_tasks(args.queued_dir, args.executed_dir, args.memory_file)
    
    # Process commands
    if args.summary:
        display_task_summary(tasks)
    
    elif args.show:
        display_task_details(args.show, tasks)
        if args.output:
            save_task_output(args.show, args.output, tasks)
    
    elif args.delete:
        if delete_task(args.delete, args.queued_dir, args.executed_dir, args.memory_file):
            print(f"Task {args.delete} deleted successfully.")
        else:
            print(f"Task {args.delete} not found or could not be deleted.")
    
    elif args.repair:
        repair_memory_file(args.memory_file)

if __name__ == "__main__":
    main() 