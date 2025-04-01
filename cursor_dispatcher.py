#!/usr/bin/env python3
"""
Cursor Dispatcher

Handles dispatching prompt tasks to Cursor by creating prompt files and executing
them via command line interface. Acts as the bridge between simulation and real execution.
"""

import os
import sys
import json
import time
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('cursor_dispatcher.log')
    ]
)
logger = logging.getLogger('cursor_dispatcher')

class CursorDispatcher:
    """
    Dispatches prompt tasks to Cursor by creating prompt files and executing 
    them via the Cursor CLI.
    """
    
    def __init__(self, 
                 project_dir: str = ".", 
                 prompts_dir: str = "prompts", 
                 output_dir: str = "output",
                 cursor_binary: Optional[str] = None,
                 auto_mode: bool = False,
                 debug: bool = False):
        """
        Initialize the Cursor Dispatcher.
        
        Args:
            project_dir: Base project directory
            prompts_dir: Directory for storing prompt files
            output_dir: Directory for storing output files
            cursor_binary: Path to the Cursor binary
            auto_mode: Whether to run in automatic mode without confirmation
            debug: Whether to run in debug mode
        """
        self.project_dir = os.path.abspath(project_dir)
        self.prompts_dir = os.path.join(self.project_dir, prompts_dir)
        self.output_dir = os.path.join(self.project_dir, output_dir)
        
        # Create directories if they don't exist
        os.makedirs(self.prompts_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Find the Cursor binary if not specified
        self.cursor_binary = cursor_binary or self._find_cursor_binary()
        
        # Configuration
        self.auto_mode = auto_mode
        self.debug = debug
        
        if self.debug:
            logger.setLevel(logging.DEBUG)
            
        logger.debug(f"Initialized CursorDispatcher with project_dir={self.project_dir}, "
                    f"prompts_dir={self.prompts_dir}, output_dir={self.output_dir}, "
                    f"cursor_binary={self.cursor_binary}, auto_mode={auto_mode}")
    
    def _find_cursor_binary(self) -> str:
        """Find the Cursor binary path."""
        # Try common locations based on OS
        if sys.platform == "win32":
            # Windows
            common_paths = [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Cursor\Cursor.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Cursor\Cursor.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Cursor\Cursor.exe")
            ]
        elif sys.platform == "darwin":
            # macOS
            common_paths = [
                "/Applications/Cursor.app/Contents/MacOS/Cursor",
                os.path.expanduser("~/Applications/Cursor.app/Contents/MacOS/Cursor")
            ]
        else:
            # Linux or other
            common_paths = [
                "/usr/bin/cursor",
                "/usr/local/bin/cursor",
                os.path.expanduser("~/.local/bin/cursor")
            ]
            
        for path in common_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
                
        # If we couldn't find the binary, use 'cursor' and hope it's in PATH
        return "cursor"
    
    def create_prompt_file(self, task: Dict, template_content: Optional[str] = None) -> str:
        """
        Create a prompt file for the given task.
        
        Args:
            task: Task dictionary with template_name, params, and id
            template_content: Optional template content to use instead of loading from a file
            
        Returns:
            Path to the created prompt file
        """
        task_id = task.get("id", str(int(time.time())))
        template_name = task.get("template_name", "custom")
        
        # Load template content if not provided
        if template_content is None:
            template_path = self._get_template_path(template_name)
            try:
                with open(template_path, "r") as f:
                    template_content = f.read()
            except (FileNotFoundError, IOError) as e:
                raise ValueError(f"Failed to load template {template_name}: {str(e)}")
        
        # Get parameters for substitution
        params = task.get("params", {})
        
        # Simple template substitution
        for key, value in params.items():
            template_content = template_content.replace(f"{{{{{key}}}}}", str(value))
        
        # Create prompt file
        prompt_filename = f"prompt_{task_id}.prompt.md"
        prompt_path = os.path.join(self.prompts_dir, prompt_filename)
        
        try:
            with open(prompt_path, "w") as f:
                f.write(template_content)
            logger.debug(f"Created prompt file at {prompt_path}")
            return prompt_path
        except Exception as e:
            logger.error(f"Failed to create prompt file: {str(e)}")
            raise
    
    def create_prompt_json(self, task: Dict) -> str:
        """
        Create a .prompt.json file for the given task.
        
        Args:
            task: Task dictionary with template_name, params, and id
            
        Returns:
            Path to the created .prompt.json file
        """
        task_id = task.get("id", str(int(time.time())))
        
        # Create simplified json with the necessary fields for Cursor
        prompt_json = {
            "id": task_id,
            "template": task.get("template_name", "custom"),
            "params": task.get("params", {}),
            "target_output": task.get("target_output", "default"),
            "auto": self.auto_mode
        }
        
        # Create .prompt.json file
        json_filename = f"prompt_{task_id}.prompt.json"
        json_path = os.path.join(self.prompts_dir, json_filename)
        
        try:
            with open(json_path, "w") as f:
                json.dump(prompt_json, f, indent=2)
            logger.debug(f"Created prompt JSON at {json_path}")
            return json_path
        except Exception as e:
            logger.error(f"Failed to create prompt JSON: {str(e)}")
            raise
    
    def execute_prompt(self, prompt_path: str) -> Tuple[bool, Dict]:
        """
        Execute a prompt using Cursor CLI.
        
        Args:
            prompt_path: Path to the prompt file
            
        Returns:
            Tuple of (success, result_data)
        """
        if not self.cursor_binary:
            raise ValueError("Cursor binary not found")
            
        # Check if the file exists
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
            
        # Determine command arguments
        args = [
            self.cursor_binary,
            "--prompt-file", prompt_path
        ]
        
        if self.auto_mode:
            args.append("--auto")
            
        if self.debug:
            args.append("--debug")
        
        logger.info(f"Executing Cursor with args: {args}")
        
        try:
            # Execute the command
            start_time = time.time()
            
            result = subprocess.run(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Process the result
            output = result.stdout
            error = result.stderr
            return_code = result.returncode
            
            if return_code == 0:
                logger.info(f"Cursor execution successful, took {execution_time:.2f}s")
                
                # Parse output to find generated files
                output_files = self._extract_generated_files(output)
                
                result_data = {
                    "success": True,
                    "return_code": return_code,
                    "execution_time": execution_time,
                    "output": output,
                    "generated_files": output_files
                }
                return True, result_data
            else:
                logger.error(f"Cursor execution failed with code {return_code}")
                logger.error(f"Error output: {error}")
                
                result_data = {
                    "success": False,
                    "return_code": return_code,
                    "execution_time": execution_time,
                    "error": error,
                    "output": output
                }
                return False, result_data
                
        except Exception as e:
            logger.error(f"Error executing Cursor: {str(e)}", exc_info=True)
            return False, {"success": False, "error": str(e)}
    
    def dispatch_task(self, task: Dict) -> Tuple[bool, Dict]:
        """
        Dispatch a task to Cursor.
        
        Args:
            task: Task dictionary with template_name, params, and id
            
        Returns:
            Tuple of (success, result_data)
        """
        try:
            # Create the prompt file
            prompt_path = self.create_prompt_file(task)
            
            # Create the JSON file (for reference)
            json_path = self.create_prompt_json(task)
            
            # Execute the prompt
            success, result = self.execute_prompt(prompt_path)
            
            # Record execution metadata
            result["task_id"] = task.get("id")
            result["prompt_path"] = prompt_path
            result["json_path"] = json_path
            result["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Save the execution result
            self._save_execution_result(task.get("id"), result)
            
            return success, result
            
        except Exception as e:
            logger.error(f"Error dispatching task: {str(e)}", exc_info=True)
            return False, {"success": False, "error": str(e)}
    
    def _get_template_path(self, template_name: str) -> str:
        """Get the path to a template file."""
        # Handle template names with or without path separators
        if os.path.sep in template_name:
            # Template name contains path separators, use it directly
            template_path = os.path.join(
                self.project_dir, "templates", template_name)
        else:
            # Try to find the template in the templates directory
            template_path = os.path.join(
                self.project_dir, "templates", template_name)
        
        # Add .prompt.md extension if not present
        if not template_path.endswith(".prompt.md"):
            template_path += ".prompt.md"
            
        return template_path
    
    def _save_execution_result(self, task_id: str, result: Dict) -> None:
        """Save the execution result to a file."""
        result_dir = os.path.join(self.project_dir, "execution_results")
        os.makedirs(result_dir, exist_ok=True)
        
        result_path = os.path.join(result_dir, f"result_{task_id}.json")
        
        try:
            with open(result_path, "w") as f:
                json.dump(result, f, indent=2)
            logger.debug(f"Execution result saved to {result_path}")
        except Exception as e:
            logger.error(f"Failed to save execution result: {str(e)}")
    
    def _extract_generated_files(self, output: str) -> List[str]:
        """
        Extract generated files from Cursor output.
        
        This is a simple implementation that looks for lines containing
        'Generated file:' or similar patterns. In a real implementation,
        this would need to be adapted to the actual output format of Cursor.
        """
        generated_files = []
        
        # Look for lines containing typical file generation indicators
        indicators = [
            "Generated file:",
            "Created file:",
            "Wrote to file:",
            "Output file:"
        ]
        
        for line in output.splitlines():
            for indicator in indicators:
                if indicator in line:
                    # Extract the file path (everything after the indicator)
                    file_path = line.split(indicator, 1)[1].strip()
                    if file_path and os.path.exists(file_path):
                        generated_files.append(file_path)
                        break
        
        return generated_files


def main():
    """Main entry point for the cursor dispatcher."""
    parser = argparse.ArgumentParser(description="Dispatch prompt tasks to Cursor")
    
    parser.add_argument("--task-file", "-f", type=str, 
                      help="Path to JSON file containing a task to execute")
    parser.add_argument("--task-dir", "-d", type=str,
                      help="Directory containing .prompt.json files to execute")
    parser.add_argument("--cursor-binary", "-c", type=str,
                      help="Path to the Cursor binary")
    parser.add_argument("--auto", "-a", action="store_true",
                      help="Run in automatic mode without confirmation")
    parser.add_argument("--debug", action="store_true",
                      help="Run in debug mode")
    parser.add_argument("--project-dir", "-p", type=str, default=".",
                      help="Project directory")
    
    args = parser.parse_args()
    
    if not args.task_file and not args.task_dir:
        logger.error("Either --task-file or --task-dir must be specified")
        sys.exit(1)
    
    # Create a dispatcher
    dispatcher = CursorDispatcher(
        project_dir=args.project_dir,
        cursor_binary=args.cursor_binary,
        auto_mode=args.auto,
        debug=args.debug
    )
    
    # Process a single task file
    if args.task_file:
        if not os.path.exists(args.task_file):
            logger.error(f"Task file not found: {args.task_file}")
            sys.exit(1)
            
        try:
            with open(args.task_file, "r") as f:
                task = json.load(f)
                
            logger.info(f"Dispatching task from {args.task_file}")
            success, result = dispatcher.dispatch_task(task)
            
            if success:
                logger.info("Task execution successful")
                sys.exit(0)
            else:
                logger.error("Task execution failed")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"Error processing task file: {str(e)}", exc_info=True)
            sys.exit(1)
    
    # Process all task files in a directory
    if args.task_dir:
        if not os.path.exists(args.task_dir):
            logger.error(f"Task directory not found: {args.task_dir}")
            sys.exit(1)
            
        task_files = [f for f in os.listdir(args.task_dir) if f.endswith(".prompt.json")]
        
        if not task_files:
            logger.error(f"No .prompt.json files found in {args.task_dir}")
            sys.exit(1)
            
        successful = 0
        failed = 0
        
        for task_file in task_files:
            task_path = os.path.join(args.task_dir, task_file)
            
            try:
                with open(task_path, "r") as f:
                    task = json.load(f)
                    
                logger.info(f"Dispatching task from {task_path}")
                success, result = dispatcher.dispatch_task(task)
                
                if success:
                    successful += 1
                else:
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Error processing task file {task_path}: {str(e)}", exc_info=True)
                failed += 1
        
        logger.info(f"Execution complete: {successful} successful, {failed} failed")
        
        if failed > 0:
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    main() 