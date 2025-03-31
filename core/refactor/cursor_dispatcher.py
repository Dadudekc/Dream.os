#!/usr/bin/env python3
"""
cursor_dispatcher.py

Handles loading, rendering, and orchestrating execution of Cursor Jinja2 templates,
and outputs .py + .prompt.md files that Cursor can read and act on.

This script implements a workflow that:
1. Renders Jinja2 templates for various stages of development
2. Sends them to Cursor with initial code stubs
3. Waits for user to run the prompt in Cursor and make edits
4. Loads the edited code for the next step
5. Continues through the workflow with testing, UX simulation, and refactoring

Usage:
    python cursor_dispatcher.py  # Interactive mode with user input at each step
    python cursor_dispatcher.py --auto  # Automated mode, skips waiting for user input
    
    # Test mode for generating unit tests for a specific file:
    python cursor_dispatcher.py --mode test --file path/to/file.py
    
    # Save generated tests to a specific location:
    python cursor_dispatcher.py --mode test --file path/to/file.py --output-test tests/test_file.py
    
    # Specify module name for proper imports:
    python cursor_dispatcher.py --mode test --file path/to/file.py --module-name myproject.module
    
    # With retries and longer timeout:
    python cursor_dispatcher.py --mode test --file path/to/file.py --retry 2 --timeout 60
    
    # Generate tests without executing them:
    python cursor_dispatcher.py --mode test --file path/to/file.py --skip-tests
"""

import logging
import argparse
import subprocess
import json
import time
import os
from pathlib import Path
from jinja2 import Template
from typing import Dict, Tuple, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CursorDispatcher")

class CursorDispatcher:
    def __init__(self, templates_dir="D:/overnight_scripts/chat_mate/templates/prompt_templates", output_dir="cursor_prompts/outputs"):
        self.templates_path = Path(templates_dir)
        self.output_path = Path(output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)

        if not self.templates_path.exists():
            raise FileNotFoundError(f"Templates directory not found: {self.templates_path}")
        
        logger.info(f"CursorDispatcher initialized at: {self.templates_path}")
        
        # Create a timestamp for this session
        self._create_timestamp()

    def _create_timestamp(self):
        """Creates a timestamp file for the current session"""
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        timestamp_file = Path("timestamp.txt")
        timestamp_file.write_text(timestamp, encoding="utf-8")
        return timestamp
        
    def load_and_render(self, template_name: str, context: Dict[str, str]) -> str:
        template_path = self.templates_path / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        raw_template = template_path.read_text(encoding="utf-8", errors="replace")
        template = Template(raw_template)
        rendered_output = template.render(**context)

        logger.info(f"Rendered template: {template_name}")
        return rendered_output

    def run_prompt(self, template_name: str, context: Dict[str, str]) -> str:
        prompt_output = self.load_and_render(template_name, context)
        logger.info(f"Prompt ready for Cursor execution: {template_name}")
        return prompt_output

    def send_to_cursor(self, code_output: str, prompt_text: str, base_filename="generated_tab") -> None:
        code_file = self.output_path / f"{base_filename}.py"
        prompt_file = self.output_path / f"{base_filename}.prompt.md"

        code_file.write_text(code_output, encoding="utf-8")
        prompt_file.write_text(prompt_text, encoding="utf-8")

        logger.info(f"✅ Files prepared for Cursor execution:")
        logger.info(f"- {code_file.resolve()}")
        logger.info(f"- {prompt_file.resolve()}")
        
    def wait_for_cursor_edit(self, base_filename="generated_tab", skip_wait=False) -> str:
        """
        Waits for the user to edit a file in Cursor and then loads the updated content.
        
        Args:
            base_filename: Base name of the file (without extension) to wait for edits on
            skip_wait: If True, skips waiting for user input and just returns the file content
            
        Returns:
            The updated file content after user edits in Cursor
            
        Raises:
            FileNotFoundError: If the generated file doesn't exist
            Exception: For any other errors during file loading
        """
        try:
            file_path = self.output_path / f"{base_filename}.py"
            
            if not skip_wait:
                prompt_msg = f"\n🕹️  Open '{base_filename}.py' in Cursor, run the prompt (Ctrl+Enter), then accept the output."
                input(f"{prompt_msg}\nOnce done, press ENTER to continue...")
            
            if not file_path.exists():
                raise FileNotFoundError(f"Could not find generated file at: {file_path}")
                
            updated_content = file_path.read_text(encoding="utf-8", errors="replace")
            logger.info(f"✅ Loaded code from {base_filename}.py")
            return updated_content
        except KeyboardInterrupt:
            logger.warning("Process interrupted by user.")
            raise
        except Exception as e:
            logger.error(f"Error loading generated code: {str(e)}")
            raise
            
    def wait_for_cursor_edit_with_timeout(self, base_filename="generated_tab", timeout_seconds=300) -> Tuple[bool, str]:
        """
        Waits for the user to edit a file in Cursor with a timeout option, polling for changes.
        
        Args:
            base_filename: Base name of the file (without extension) to wait for edits on
            timeout_seconds: Maximum time to wait in seconds before giving up
            
        Returns:
            A tuple of (success, content) where success is True if edit was detected within timeout
            
        Raises:
            FileNotFoundError: If the generated file doesn't exist
        """
        file_path = self.output_path / f"{base_filename}.py"
        if not file_path.exists():
            raise FileNotFoundError(f"Could not find generated file at: {file_path}")
            
        # Get the initial state of the file
        try:
            initial_content = file_path.read_text(encoding="utf-8", errors="replace")
            initial_mtime = file_path.stat().st_mtime
        except Exception as e:
            logger.error(f"Error getting initial file state: {e}")
            return False, ""
            
        prompt_msg = f"\n🕹️  Open '{base_filename}.py' in Cursor, run the prompt (Ctrl+Enter), then accept the output."
        print(f"{prompt_msg}\nWaiting up to {timeout_seconds} seconds for changes...")
        
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            try:
                # Check if the file has been modified
                current_mtime = file_path.stat().st_mtime
                if current_mtime > initial_mtime:
                    # File has been modified, read the new content
                    updated_content = file_path.read_text(encoding="utf-8", errors="replace")
                    
                    # Check if content actually changed (not just metadata)
                    if updated_content != initial_content:
                        logger.info(f"✅ Detected changes in {base_filename}.py after {int(time.time() - start_time)} seconds")
                        return True, updated_content
                        
                # Wait a short time before checking again
                time.sleep(1)
                
                # Periodically log that we're still waiting
                elapsed = time.time() - start_time
                if elapsed % 30 < 1:  # Log approximately every 30 seconds
                    logger.info(f"Still waiting for changes... ({int(elapsed)}s elapsed)")
                    
            except Exception as e:
                logger.error(f"Error while polling for file changes: {e}")
                return False, initial_content
                
        # Timeout expired
        logger.warning(f"⏱️ Timeout waiting for changes to {base_filename}.py after {timeout_seconds} seconds")
        return False, initial_content
        
    def send_and_wait(self, code_output: str, prompt_text: str, base_filename="generated_tab", skip_wait=False, wait_timeout=0) -> str:
        """
        Combines send_to_cursor and wait_for_cursor_edit into a single operation.
        
        Args:
            code_output: Initial code to send to Cursor
            prompt_text: Prompt text to guide Cursor's editing
            base_filename: Base name for the files
            skip_wait: If True, skips waiting for user input
            wait_timeout: If > 0, use timed waiting (polling) instead of blocking on user input
            
        Returns:
            The content of the file after user edits in Cursor (or immediately if skip_wait is True)
        """
        self.send_to_cursor(code_output, prompt_text, base_filename)
        
        if skip_wait:
            return self.wait_for_cursor_edit(base_filename, skip_wait=True)
        elif wait_timeout > 0:
            success, content = self.wait_for_cursor_edit_with_timeout(base_filename, timeout_seconds=wait_timeout)
            if not success:
                logger.warning("Timeout waiting for edits. Proceeding with latest content.")
            return content
        else:
            return self.wait_for_cursor_edit(base_filename, skip_wait=False)
        
    def run_tests(self, code_file_path: str, test_file_path: Optional[str] = None, timeout: int = 30, retry_count: int = 0) -> Tuple[bool, str]:
        """
        Run tests for a given code file. If test_file_path is not provided,
        it will attempt to find or generate a test file.
        
        Args:
            code_file_path: Path to the code file to test
            test_file_path: Optional path to the test file. If not provided, will try to find or generate one.
            timeout: Maximum time to wait for test execution in seconds
            retry_count: Number of times to retry failed tests
            
        Returns:
            Tuple of (success: bool, output: str)
        """
        try:
            code_path = Path(code_file_path)
            if not code_path.exists():
                return False, f"Code file not found: {code_file_path}"
            
            # If no test file provided, try to find or generate one
            if not test_file_path:
                test_file_path = self._find_or_generate_test_file(code_file_path)
                if not test_file_path:
                    return False, f"Could not find or generate test file for {code_file_path}"
            
            test_path = Path(test_file_path)
            if not test_path.exists():
                return False, f"Test file not found: {test_file_path}"
            
            # Run pytest with output capture
            cmd = ["pytest", "-v", str(test_path)]
            
            for attempt in range(retry_count + 1):
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                    
                    success = result.returncode == 0
                    output = result.stdout if success else f"{result.stdout}\n{result.stderr}"
                    
                    if success:
                        logger.info(f"Tests passed for {code_file_path}")
                        return True, output
                    
                    if attempt < retry_count:
                        logger.warning(f"Test attempt {attempt + 1} failed, retrying...")
                        time.sleep(1)  # Brief pause between retries
                    else:
                        logger.error(f"Tests failed for {code_file_path} after {retry_count + 1} attempts")
                        return False, output
                        
                except subprocess.TimeoutExpired:
                    if attempt < retry_count:
                        logger.warning(f"Test attempt {attempt + 1} timed out, retrying...")
                        continue
                    return False, f"Tests timed out after {timeout} seconds"
                    
        except Exception as e:
            logger.error(f"Error running tests: {str(e)}")
            return False, str(e)

    def _find_or_generate_test_file(self, code_file_path: str) -> Optional[str]:
        """
        Find an existing test file or generate a new one for the given code file.
        """
        code_path = Path(code_file_path)
        
        # Common test file patterns
        test_patterns = [
            code_path.parent / f"test_{code_path.name}",
            code_path.parent / f"{code_path.stem}_test{code_path.suffix}",
            code_path.parent / "tests" / f"test_{code_path.name}",
            Path("tests") / f"test_{code_path.name}"
        ]
        
        # Try to find existing test file
        for test_path in test_patterns:
            if test_path.exists():
                return str(test_path)
        
        # If no test file found and auto-generation is enabled, generate one
        try:
            from generate_missing_tests import generate_test_file
            test_path = code_path.parent / f"test_{code_path.name}"
            generate_test_file(str(code_path), str(test_path))
            if test_path.exists():
                return str(test_path)
        except Exception as e:
            logger.error(f"Failed to generate test file: {str(e)}")
        
        return None

    def git_commit_changes(self, message: str, file_paths: list) -> bool:
        """
        Commit changes to Git with the given message and files.
        
        Args:
            message: Commit message
            file_paths: List of files to commit
            
        Returns:
            bool: True if commit was successful, False otherwise
        """
        try:
            # Ensure all files exist
            for file_path in file_paths:
                if not Path(file_path).exists():
                    logger.error(f"File not found: {file_path}")
                    return False
            
            # Stage files
            for file_path in file_paths:
                subprocess.run(["git", "add", file_path], check=True)
            
            # Create commit
            result = subprocess.run(
                ["git", "commit", "-m", message],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully committed changes: {message}")
                
                # Try to push if remote is configured
                try:
                    push_result = subprocess.run(
                        ["git", "push"],
                        capture_output=True,
                        text=True
                    )
                    if push_result.returncode == 0:
                        logger.info("Successfully pushed changes")
                    else:
                        logger.warning(f"Push failed: {push_result.stderr}")
                except Exception as e:
                    logger.warning(f"Failed to push changes: {str(e)}")
                
                return True
            else:
                logger.error(f"Commit failed: {result.stderr}")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Git operation failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error during Git commit: {str(e)}")
            return False

    def execute_prompt_sequence(self, sequence_name: str, initial_context: Dict, skip_wait=False, wait_timeout=0):
        """
        Executes a sequence of prompts defined in a JSON configuration file.

        Args:
            sequence_name: Name or full path of the prompt sequence to execute
            initial_context: Initial context to start the sequence with
            skip_wait: If True, skips waiting for user input
            wait_timeout: Timeout in seconds for waiting for Cursor edits

        Returns:
            The final output of the sequence
            
        Raises:
            FileNotFoundError: If the sequence file doesn't exist
            json.JSONDecodeError: If the sequence file contains invalid JSON
            ValueError: If the sequence file has an invalid structure
        """
        # Allow full path or just a name
        sequence_path = Path(sequence_name)
        if not sequence_path.exists():
            sequence_path = self.templates_path / "sequences" / f"{sequence_name}.json"


        if not sequence_path.exists():
            logger.error(f"Prompt sequence not found: {sequence_name}")
            raise FileNotFoundError(f"Prompt sequence not found: {sequence_name}")

            
        try:
            with open(sequence_path, 'r', encoding="utf-8") as f:
                try:
                    sequence_data = json.load(f)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in sequence file {sequence_path}: {e}")
                    raise
                
            # Validate sequence structure
            if 'steps' not in sequence_data:
                raise ValueError(f"Invalid sequence file: 'steps' key not found in {sequence_path}")
                
            logger.info(f"🔄 Starting prompt sequence: {sequence_name} with {len(sequence_data['steps'])} steps")
            
            # Initialize context with provided initial context
            context = initial_context.copy()
            current_code = sequence_data.get("initial_code", "# Code will be generated through the sequence")
            
            # Track results for each step
            sequence_results = {
                "sequence_name": sequence_name,
                "steps": [],
                "started_at": Path("timestamp.txt").read_text(encoding="utf-8").strip() if Path("timestamp.txt").exists() else None,
                "context": context
            }
            
            # Process each step in the sequence
            for i, step in enumerate(sequence_data["steps"]):
                step_num = i + 1
                
                # Validate step structure
                if "template" not in step:
                    logger.error(f"Step {step_num} is missing required 'template' key")
                    raise ValueError(f"Invalid step {step_num}: 'template' key not found")
                    
                template_name = step["template"]
                output_file = step.get("output_file", f"step_{step_num}")
                
                # Update context with step-specific context
                step_context = context.copy()
                step_context.update(step.get("context", {}))
                step_context["CODE_FILE_CONTENT"] = current_code
                
                logger.info(f"Step {step_num}/{len(sequence_data['steps'])}: {template_name}")
                
                # Run the prompt for this step
                prompt_text = self.run_prompt(template_name, step_context)
                
                # Send to Cursor and wait for edit
                try:
                    updated_code = self.send_and_wait(
                        current_code, 
                        prompt_text, 
                        output_file, 
                        skip_wait=skip_wait,
                        wait_timeout=step.get("wait_timeout", 0)
                    )
                    current_code = updated_code
                    
                    # Update the context with the new code for next steps
                    context["CODE_FILE_CONTENT"] = current_code
                    
                    # Run tests if specified for this step
                    run_tests_for_step = step.get("run_tests", False)
                    test_results = None
                    
                    if run_tests_for_step:
                        code_path = self.output_path / f"{output_file}.py"
                        success, output = self.run_tests(str(code_path))
                        test_results = {"success": success, "output": output}
                        logger.info(f"Step {step_num} tests: {'✅ PASSED' if success else '❌ FAILED'}")
                    
                    # Record step results
                    step_result = {
                        "step": step_num,
                        "template": template_name,
                        "output_file": output_file,
                        "successful": True,
                        "test_results": test_results
                    }
                    sequence_results["steps"].append(step_result)
                    
                except Exception as e:
                    logger.error(f"Error in sequence step {step_num}: {e}")
                    step_result = {
                        "step": step_num,
                        "template": template_name,
                        "output_file": output_file,
                        "successful": False,
                        "error": str(e)
                    }
                    sequence_results["steps"].append(step_result)
                    
                    # Check if we should continue on error
                    if not step.get("continue_on_error", False):
                        logger.error(f"Stopping sequence due to error in step {step_num}")
                        break
            
            # Save sequence results
            results_file = self.output_path / f"{sequence_name}_results.json"
            with open(results_file, 'w', encoding="utf-8") as f:
                json.dump(sequence_results, f, indent=2)
                
            logger.info(f"✅ Completed prompt sequence: {sequence_name}")
            return current_code
            
        except Exception as e:
            logger.error(f"Failed to execute prompt sequence: {e}")
            raise
            
    def install_git_hook(self, hook_type: str = "post-commit") -> bool:
        """
        Installs a Git hook that runs after commit operations.
        
        Args:
            hook_type: Type of Git hook to install
            
        Returns:
            True if hook was installed successfully, False otherwise
        """
        try:
            # Check if we're in a git repository
            try:
                repo_root = subprocess.run(
                    ["git", "rev-parse", "--show-toplevel"], 
                    check=True, 
                    capture_output=True,
                    text=True
                ).stdout.strip()
            except subprocess.CalledProcessError:
                logger.error("Not inside a git repository.")
                return False
                
            hooks_dir = os.path.join(repo_root, ".git", "hooks")
            hook_path = os.path.join(hooks_dir, hook_type)
            
            # Create the hook script
            hook_content = f"""#!/bin/sh
# Git {hook_type} hook installed by CursorDispatcher
# Records successful commits for analytics

# Get the commit message
COMMIT_MSG=$(git log -1 --pretty=%B)

# Create analytics record
echo "{{\\"timestamp\\": \\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\\", \\"hook\\": \\"{hook_type}\\", \\"message\\": \\"$COMMIT_MSG\\"}}" >> {os.path.join(repo_root, "cursor_prompts", "outputs", "git_analytics.json")}

# Continue with normal Git process
exit 0
"""
            # Write the hook script
            with open(hook_path, 'w') as f:
                f.write(hook_content)
                
            # Make the hook executable
            os.chmod(hook_path, 0o755)
            
            logger.info(f"✅ Successfully installed {hook_type} hook")
            return True
            
        except Exception as e:
            logger.error(f"Error installing Git hook: {str(e)}")
            return False


# Execution Flow
if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Cursor Dispatcher - Orchestrate Cursor prompt execution")
    parser.add_argument("--mode", choices=["test"], help="Execution mode: 'test' generates unit tests for the specified file")
    parser.add_argument("--file", help="Target file for test generation (required when --mode=test)")
    parser.add_argument("--output-test", help="Path to save the generated test file (optional for test mode)")
    parser.add_argument("--module-name", help="Module name to use when importing the tested file (optional for test mode)")
    parser.add_argument("--retry", type=int, default=0, help="Number of retry attempts for test execution (default: 0)")
    parser.add_argument("--timeout", type=int, default=30, help="Test execution timeout in seconds (default: 30)")
    parser.add_argument("--wait-timeout", type=int, default=0, 
                        help="Timeout in seconds for waiting for Cursor edits (0 = wait indefinitely, default)")
    parser.add_argument("--auto", action="store_true", help="Run in automated mode, skipping user input pauses")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests (in test mode, only generates tests without executing them)")
    parser.add_argument("--sequence", help="Run a predefined prompt sequence instead of the default flow")
    parser.add_argument("--git-commit", action="store_true", help="Automatically commit changes at the end of the process")
    parser.add_argument("--install-hooks", action="store_true", help="Install Git hooks for analytics")
    parser.add_argument(
        "--templates",
        type=str,
        default="D:/overnight_scripts/chat_mate/templates/prompt_templates",
        help="Path to the directory containing Jinja2 templates"
    )
    args = parser.parse_args()
    
    # Handle test mode if provided
    if args.mode == "test" and args.file:
        # Use a specific test prompt flow for generating tests
        dispatcher = CursorDispatcher(templates_dir=args.templates)
        
        logger.info(f"🧪 Generating tests for: {args.file}")
        
        # Read the target file content
        target_file_path = Path(args.file)
        if not target_file_path.exists():
            logger.error(f"❌ Target file not found: {args.file}")
            exit(1)
            
        try:
            logger.info("📝 Reading target file and preparing test prompt...")
            target_code = target_file_path.read_text(encoding="utf-8", errors="replace")
            
            # Create a more detailed test prompt
            test_prompt = f"""
# TASK: Generate Unit Tests

## CODE TO TEST
```python
{target_code}
```

## REQUIREMENTS
- Create thorough unittest tests for this code
- Cover edge cases and normal operation
- Mock external dependencies if needed
- Make the tests runnable with unittest module
- Return ONLY the test code
"""
            
            # If module name is provided, add it to the prompt
            if args.module_name:
                test_prompt += f"\n## MODULE IMPORT\nWhen importing the code, use: `import {args.module_name}`"
            else:
                # Provide import suggestions based on file location
                file_basename = target_file_path.stem
                file_dir = target_file_path.parent
                test_prompt += f"\n## IMPORT SUGGESTION\nSince no module name was specified, please include these lines at the top of your test:\n```python\nimport sys\nimport os\nsys.path.append('{file_dir}')\nfrom {file_basename} import *\n```"
            
            try:
                dispatcher.send_to_cursor(
                    code_output="import unittest\n\n# Tests will be generated by Cursor",
                    prompt_text=test_prompt,
                    base_filename="generated_test"
                )
            except Exception as e:
                logger.error(f"Failed to send to cursor: {e}")
                raise
            
            # Read the generated test file
            generated_test_file = dispatcher.wait_for_cursor_edit(base_filename="generated_test")
            
            # Run tests
            success, output = dispatcher.run_tests(args.file)
            
            if success:
                logger.info("Tests passed!")
            else:
                logger.error(f"Tests failed. Output:\n{output}")
            
            # Commit changes if requested
            if args.git_commit:
                dispatcher.git_commit_changes("Updated tests", [args.file])
            
            # Save the generated test file
            if args.output_test:
                test_output_path = Path(args.output_test)
                test_output_path.write_text(generated_test_file, encoding="utf-8")
                logger.info(f"✅ Generated test file saved to: {test_output_path}")
            
        except Exception as e:
            logger.error(f"Error in test mode: {e}")
            exit(1)

    else:
        # Interactive mode
        dispatcher = CursorDispatcher()
        
        # Run a sequence if specified
        if args.sequence:
            dispatcher.execute_prompt_sequence(args.sequence, {}, skip_wait=args.wait_timeout > 0, wait_timeout=args.wait_timeout)
        else:
            # Run default interactive mode
            dispatcher.execute_prompt_sequence("default", {}, skip_wait=args.wait_timeout > 0, wait_timeout=args.wait_timeout)
