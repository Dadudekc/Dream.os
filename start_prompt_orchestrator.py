#!/usr/bin/env python3
"""
Dream.OS Prompt Orchestrator Startup Script

This script starts both the Dream.OS main application and the task watcher
in separate processes for a complete prompt orchestration environment.
"""

import os
import sys
import subprocess
import logging
import time
import argparse
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('prompt_orchestrator.log')
    ]
)

logger = logging.getLogger('orchestrator')

def ensure_directories():
    """Ensure all required directories exist."""
    directories = [
        ".cursor/queued_tasks",
        ".cursor/executed_tasks",
        "memory",
        "templates/cursor_templates",
        "output"
    ]
    
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {path}")

def start_task_watcher():
    """Start the task watcher in a separate process."""
    logger.info("Starting task watcher...")
    
    # Start the task watcher script
    process = subprocess.Popen(
        [sys.executable, "scripts/task_watcher.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    logger.info(f"Task watcher started with PID: {process.pid}")
    return process

def start_dream_os():
    """Start the Dream.OS main application."""
    logger.info("Starting Dream.OS...")
    
    # Start the Dream.OS main window
    process = subprocess.Popen(
        [sys.executable, "DreamOsMainWindow_full.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    logger.info(f"Dream.OS started with PID: {process.pid}")
    return process

def monitor_processes(processes):
    """Monitor running processes and log their output."""
    try:
        while all(p.poll() is None for p in processes):
            for name, process in processes.items():
                # Read output without blocking
                stdout_line = process.stdout.readline() if process.stdout else ""
                stderr_line = process.stderr.readline() if process.stderr else ""
                
                if stdout_line:
                    logger.info(f"{name} stdout: {stdout_line.strip()}")
                if stderr_line:
                    logger.error(f"{name} stderr: {stderr_line.strip()}")
            
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        for name, process in processes.items():
            logger.info(f"Terminating {name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
                logger.info(f"{name} terminated gracefully")
            except subprocess.TimeoutExpired:
                logger.warning(f"{name} did not terminate, killing...")
                process.kill()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Start Dream.OS Prompt Orchestrator")
    parser.add_argument("--no-watcher", action="store_true", help="Don't start the task watcher")
    parser.add_argument("--no-ui", action="store_true", help="Don't start the UI")
    args = parser.parse_args()
    
    logger.info("Starting Dream.OS Prompt Orchestrator")
    
    # Ensure directories exist
    ensure_directories()
    
    processes = {}
    
    # Start task watcher if requested
    if not args.no_watcher:
        watcher_process = start_task_watcher()
        processes["Task Watcher"] = watcher_process
    
    # Start Dream.OS if requested
    if not args.no_ui:
        dream_os_process = start_dream_os()
        processes["Dream.OS"] = dream_os_process
    
    if processes:
        # Monitor processes
        monitor_processes(processes)
    else:
        logger.warning("No processes started. Use --help to see options.")
    
    logger.info("Dream.OS Prompt Orchestrator shutdown complete")

if __name__ == "__main__":
    main() 