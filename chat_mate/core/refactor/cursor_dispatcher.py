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
        Executes tests for the generated code file.
        
        Args:
            code_file_path: Path to the code file to test
            test_file_path: Path to the test file (if None, will be auto-generated)
            timeout: Maximum time (in seconds) to allow tests to run before timing out
            retry_count: Number of times to retry on test failures (0 = no retry)
            
        Returns:
            A tuple of (success, output)
            
        Raises:
            FileNotFoundError: If the code file or test file doesn't exist
            subprocess.TimeoutExpired: If tests exceed the timeout limit
        """
        logger.info(f"🧪 Running tests for: {code_file_path}")
        
        code_path = Path(code_file_path)
        if not code_path.exists():
            error_msg = f"Code file not found: {code_file_path}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        
        if test_file_path is None:
            # Generate a test file name based on the code file
            test_file_path = str(self.output_path / f"test_{code_path.stem}.py")
            
            # Check if we need to generate tests
            test_path = Path(test_file_path)
            if not test_path.exists():
                logger.info(f"Generating test file at: {test_file_path}")
                self._create_test_file(code_file_path, test_file_path)
        else:
            # Verify if provided test file exists
            test_path = Path(test_file_path)
            if not test_path.exists():
                error_msg = f"Test file not found: {test_file_path}"
                logger.error(f"❌ {error_msg}")
                return False, error_msg
        
        attempts = 0
        max_attempts = retry_count + 1  # Original attempt + retries
        
        while attempts < max_attempts:
            attempts += 1
            
            try:
                # Run the tests using unittest
                logger.info(f"Test attempt {attempts}/{max_attempts} with timeout {timeout}s")
                
                result = subprocess.run(
                    ["python", "-m", "unittest", test_file_path],
                    capture_output=True, 
                    text=True, 
                    timeout=timeout,
                    encoding="utf-8",
                    errors="replace"
                )
                
                output = result.stdout + "\n" + result.stderr
                success = (result.returncode == 0)
                
                if success:
                    logger.info(f"✅ Tests PASSED for {code_file_path} (attempt {attempts}/{max_attempts})")
                    break  # Exit the retry loop on success
                else:
                    logger.warning(f"❌ Tests FAILED for {code_file_path} (attempt {attempts}/{max_attempts})")
                    logger.debug(f"Test output: {output}")
                    
                    if attempts < max_attempts:
                        logger.info(f"Retrying in 2 seconds...")
                        time.sleep(2)  # Short delay before retry
                
            except subprocess.TimeoutExpired as e:
                error_msg = f"Timeout when running tests (exceeded {timeout}s): {e}"
                logger.error(f"❌ {error_msg}")
                if attempts < max_attempts:
                    logger.info(f"Retrying with longer timeout...")
                    timeout += 10  # Increase timeout for next attempt
                    time.sleep(1)
                else:
                    return False, error_msg
                
            except Exception as e:
                error_msg = f"Exception when running tests: {e}"
                logger.error(f"❌ {error_msg}")
                import traceback
                logger.debug(f"Traceback: {traceback.format_exc()}")
                if attempts < max_attempts:
                    logger.info(f"Retrying after error...")
                    time.sleep(2)
                else:
                    return False, error_msg
        
        # Create a structured test result for analysis
        test_results = {
            "success": success,
            "output": output,
            "file_tested": code_file_path,
            "test_file": test_file_path,
            "return_code": result.returncode,
            "attempts": attempts,
            "timestamp": time.time()
        }
        
        # Store results for later analysis
        results_file = self.output_path / "test_results.json"
        self._append_to_json(results_file, test_results)
            
        return success, output
    
    def _create_test_file(self, code_file_path: str, test_file_path: str) -> None:
        """
        Creates a test file for the given code file using Cursor.
        
        Args:
            code_file_path: Path to the code file
            test_file_path: Path to create the test file
            
        Raises:
            FileNotFoundError: If the code file doesn't exist
            IOError: If there are issues reading/writing files
        """
        try:
            # Read the code file with explicit encoding
            try:
                code_content = Path(code_file_path).read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                logger.error(f"Failed to read code file {code_file_path}: {e}")
                raise IOError(f"Cannot read code file: {e}")
            
            # Create a prompt for test generation
            test_prompt = f"""
# TASK: Generate Unit Tests

## CODE TO TEST
```python
{code_content}
```

## REQUIREMENTS
- Create thorough unittest tests for this code
- Cover edge cases and normal operation
- Mock external dependencies if needed
- Make the tests runnable with unittest module
- Return ONLY the test code
"""
            # Use Cursor to generate tests
            initial_test = "import unittest\n\n# Tests will be generated by Cursor"
            test_code = self.send_and_wait(initial_test, test_prompt, "generated_test", skip_wait=False)
            
            # Save the generated test code with explicit encoding
            try:
                Path(test_file_path).write_text(test_code, encoding="utf-8")
                logger.info(f"✅ Generated test file: {test_file_path}")
            except Exception as e:
                logger.error(f"Failed to write test file {test_file_path}: {e}")
                raise IOError(f"Cannot write test file: {e}")
            
        except Exception as e:
            logger.error(f"Failed to create test file: {e}")
            logger.info("Creating a minimal fallback test file instead")
            # Create a minimal test file
            minimal_test = (
                "import unittest\n\n"
                "class MinimalTest(unittest.TestCase):\n"
                "    def test_module_imports(self):\n"
                "        # This is a placeholder test\n"
                "        import sys\n"
                f"        sys.path.append('{Path(code_file_path).parent}')\n"
                f"        import {Path(code_file_path).stem}\n"
                "        self.assertTrue(True)\n\n"
                "if __name__ == '__main__':\n"
                "    unittest.main()\n"
            )
            try:
                Path(test_file_path).write_text(minimal_test, encoding="utf-8")
                logger.info(f"⚠️ Created minimal test file: {test_file_path}")
            except Exception as write_err:
                logger.critical(f"Failed to create even minimal test file: {write_err}")
                raise
    
    def _append_to_json(self, file_path: Path, data: dict) -> None:
        """
        Appends data to a JSON file, creating it if it doesn't exist.
        Takes care to preserve existing data in case of corruption.
        
        Args:
            file_path: Path to the JSON file
            data: Dictionary data to append
        """
        try:
            # Initialize with an empty list if file doesn't exist
            if not file_path.exists():
                file_path.write_text("[]", encoding="utf-8")
                
            # Read existing data
            try:
                with open(file_path, 'r', encoding="utf-8") as f:
                    json_data = json.load(f)
            except json.JSONDecodeError as json_err:
                # If JSON is corrupted, back it up and start fresh
                backup_path = file_path.with_suffix(f".corrupted.{int(time.time())}.json")
                logger.error(f"JSON file corrupted: {json_err}. Backing up to {backup_path}")
                
                # Backup the corrupted file
                try:
                    with open(file_path, 'r', encoding="utf-8") as src:
                        with open(backup_path, 'w', encoding="utf-8") as dst:
                            dst.write(src.read())
                    logger.info(f"Corrupted JSON backed up to: {backup_path}")
                except Exception as backup_err:
                    logger.error(f"Failed to backup corrupted JSON: {backup_err}")
                
                # Start fresh with an empty list
                json_data = []
                
            # Append new data
            json_data.append(data)
            
            # Write back to file
            with open(file_path, 'w', encoding="utf-8") as f:
                json.dump(json_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to append data to {file_path}: {e}")
            # Last resort: try to write just this piece of data to a new file
            try:
                fallback_path = file_path.with_suffix(f".fallback.{int(time.time())}.json")
                with open(fallback_path, 'w', encoding="utf-8") as f:
                    json.dump([data], f, indent=2)
                logger.warning(f"Saved data to fallback file: {fallback_path}")
            except Exception as fallback_err:
                logger.critical(f"Failed to save data even to fallback file: {fallback_err}")
                    
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
            
    def git_commit_changes(self, message: str, file_paths: list) -> bool:
        """
        Commits changes to Git repository.
        
        Args:
            message: Commit message
            file_paths: List of file paths to commit
            
        Returns:
            True if commit was successful, False otherwise
        """
        try:
            # Make sure we're in a git repository
            try:
                subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], 
                               check=True, 
                               capture_output=True,
                               text=True,
                               encoding="utf-8",
                               errors="replace")
            except subprocess.CalledProcessError:
                logger.error("Not inside a git repository.")
                return False
                
            # Add specified files
            files_str = " ".join(file_paths)
            add_cmd = f"git add {files_str}"
            logger.info(f"Adding files to git: {add_cmd}")
            
            try:
                subprocess.run(add_cmd, 
                              shell=True, 
                              check=True, 
                              capture_output=True,
                              text=True,
                              encoding="utf-8",
                              errors="replace")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to add files: {e.stderr}")
                return False
            
            # Create commit - handle special characters in commit message
            # Escape quotes and other special characters for shell
            safe_message = message.replace('"', '\\"').replace('$', '\\$')
            commit_cmd = f'git commit -m "{safe_message}"'
            logger.info(f"Creating commit: {commit_cmd}")
            
            try:
                result = subprocess.run(
                    commit_cmd, 
                    shell=True, 
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace"
                )
                
                if result.returncode == 0:
                    logger.info(f"✅ Successfully committed changes: {message}")
                    return True
                else:
                    logger.error(f"Failed to commit changes: {result.stderr}")
                    return False
            except Exception as e:
                logger.error(f"Error during Git commit execution: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error during Git commit: {str(e)}")
            return False
            
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
            
            dispatcher.send_to_cursor(
                code_output="import unittest\n\n# Tests will be generated by Cursor",
                prompt_text=test_prompt,
                base_filename="generated_test"
            )
            
            logger.info("✨ Test prompt prepared and sent to Cursor")
            
            if args.wait_timeout > 0:
                logger.info(f"Waiting up to {args.wait_timeout} seconds for test generation...")
                success, _ = dispatcher.wait_for_cursor_edit_with_timeout(
                    "generated_test", 
                    timeout_seconds=args.wait_timeout
                )
                if not success:
                    logger.warning("⏱️ Timeout waiting for test generation.")
                    choice = input("Continue anyway? [y/N]: ").lower().strip()
                    if choice != 'y':
                        logger.info("Aborting test generation.")
                        exit(1)
            else:
                input("[↪] Open 'generated_test.py' in Cursor, run the prompt, then press ENTER to run tests...")
            
            # Load the generated test code
            test_file_path = dispatcher.output_path / "generated_test.py"
            if not test_file_path.exists():
                logger.error("❌ No test file was generated.")
                exit(1)
                
            logger.info("📋 Generated test code successfully")
            generated_test_code = test_file_path.read_text(encoding="utf-8", errors="replace")
            
            # Save to output location if specified
            if args.output_test:
                output_path = Path(args.output_test)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(generated_test_code, encoding="utf-8")
                logger.info(f"✅ Saved generated test to: {output_path}")
                
                # Use the saved test file for running tests
                test_file_to_run = str(output_path)
            else:
                # Use the temporary test file
                test_file_to_run = str(test_file_path)
                
            # Run the tests against the target file
            if not args.skip_tests:
                logger.info("🧪 Running tests...")
                success, output = dispatcher.run_tests(
                    args.file, 
                    test_file_to_run,
                    timeout=args.timeout,
                    retry_count=args.retry
                )
                
                if success:
                    logger.info("✅ Tests passed successfully!")
                    print("[✓] Tests passed successfully.")
                else:
                    logger.warning("❌ Tests failed.")
                    print("[!] Tests failed. Details:")
                    print(output)
            else:
                logger.info("⏭️ Skipping test execution (--skip-tests flag)")
                print("[i] Tests generated but not executed.")
                
        except Exception as e:
            logger.error(f"Error in test generation mode: {e}")
            exit(1)
            
        exit(0)
    
    skip_waiting = args.auto
    run_tests = not args.skip_tests
    auto_commit = args.git_commit
    
    if skip_waiting:
        logger.info("Running in automated mode - skipping user input pauses")
    
    # Initialize dispatcher with specified (or default) templates directory
    dispatcher = CursorDispatcher(templates_dir=args.templates)
    
    # Install Git hooks if requested
    if args.install_hooks:
        if dispatcher.install_git_hook("post-commit"):
            logger.info("Git hooks installed successfully")
        else:
            logger.warning("Failed to install Git hooks")
    
    if args.sequence:
        # Run a predefined sequence of prompts
        try:
            initial_context = {
                "STRATEGY_DESCRIPTION": "Create a modular PyQt5 tab for UX testing and live preview of widgets."
            }
            final_code = dispatcher.execute_prompt_sequence(
                args.sequence, 
                initial_context, 
                skip_wait=skip_waiting,
                wait_timeout=args.wait_timeout
            )
            
            # Auto-commit if enabled
            if auto_commit:
                # Generate commit message
                commit_context = {
                    "CODE_DIFF_OR_FINAL": final_code,
                    "SEQUENCE_NAME": args.sequence
                }
                commit_message = dispatcher.run_prompt("05_commit_and_version.j2", commit_context)
                commit_message = commit_message.split("\n")[0]  # Use first line as commit message
                
                # Commit changes
                files_to_commit = [
                    str(dispatcher.output_path / f"*.py")
                ]
                if dispatcher.git_commit_changes(commit_message, files_to_commit):
                    logger.info(f"Changes committed: {commit_message}")
                else:
                    logger.warning("Failed to commit changes")
            
            exit(0)
        except Exception as e:
            logger.error(f"Failed to run sequence '{args.sequence}': {e}")
            exit(1)

    # Default flow: Strategy → Code → Test → UX → Refactor → Commit
    # Step 1: Strategy → Code
    strategy_context = {
        "STRATEGY_DESCRIPTION": "Create a modular PyQt5 tab for UX testing and live preview of widgets."
    }
    raw_prompt_1 = dispatcher.run_prompt("01_strategy_to_code.j2", strategy_context)
    initial_code = "# TODO: Cursor will generate this based on prompt\n\n" + raw_prompt_1
    
    try:
        # Send prompt to Cursor and wait for user to run it
        code_result = dispatcher.send_and_wait(initial_code, raw_prompt_1, skip_wait=skip_waiting, wait_timeout=args.wait_timeout)
    except (KeyboardInterrupt, Exception) as e:
        logger.error(f"Process halted during Step 1: {str(e)}")
        exit(1)

    # Step 2: Code → Test & Validate
    test_context = {
        "CODE_FILE_CONTENT": code_result
    }
    test_result = dispatcher.run_prompt("02_code_test_validate.j2", test_context)
    generated_file_path = dispatcher.output_path / "generated_tab.py"
    
    if run_tests:
        # Run tests on the generated code
        test_success, test_output = dispatcher.run_tests(
            str(generated_file_path), 
            timeout=args.timeout,
            retry_count=args.retry
        )
        logger.info(f"Test execution result: {'✅ PASSED' if test_success else '❌ FAILED'}")
        if not test_success:
            logger.info("\n--- Test Failure Details ---\n" + test_output)
    else:
        logger.info("Skipping test execution (--skip-tests flag)")
    
    print("\n--- Cursor Step 2 Output ---\n", test_result)

    # Step 3: Code → UX Simulation
    ux_context = {
        "CODE_FILE_CONTENT": code_result
    }
    ux_result = dispatcher.run_prompt("03_ux_simulation_feedback.j2", ux_context)
    print("\n--- Cursor Step 3 Output ---\n", ux_result)

    # Step 4: Refactor from Feedback
    feedback_context = {
        "USER_FEEDBACK": "Improve readability and handle edge cases for empty user inputs.",
        "CODE_FILE_CONTENT": code_result
    }
    refactor_prompt = dispatcher.run_prompt("04_refactor_feedback_loop.j2", feedback_context)
    
    try:
        # Send refactor prompt to Cursor and wait for user to run it
        refactored_result = dispatcher.send_and_wait(code_result, refactor_prompt, "refactored_tab", skip_wait=skip_waiting, wait_timeout=args.wait_timeout)
        print("\n--- Cursor Step 4 Output: Successfully refactored code ---")
        
        if run_tests:
            # Run tests on the refactored code
            refactored_file_path = dispatcher.output_path / "refactored_tab.py"
            refactor_test_success, refactor_test_output = dispatcher.run_tests(
                str(refactored_file_path),
                timeout=args.timeout,
                retry_count=args.retry
            )
            logger.info(f"Refactored code test result: {'✅ PASSED' if refactor_test_success else '❌ FAILED'}")
            if not refactor_test_success:
                logger.info("\n--- Refactored Test Failure Details ---\n" + refactor_test_output)
    except (KeyboardInterrupt, Exception) as e:
        logger.error(f"Process halted during Step 4: {str(e)}")
        refactored_result = code_result  # Use original code if refactoring fails
        print("\n--- Cursor Step 4 Output: Using original code due to error ---")

    # Step 5: Commit & Versioning
    commit_context = {
        "CODE_DIFF_OR_FINAL": refactored_result
    }
    commit_message = dispatcher.run_prompt("05_commit_and_version.j2", commit_context)
    print("\n--- Cursor Step 5 Output ---\n", commit_message)
    
    # Auto-commit if enabled
    if auto_commit:
        # Extract first line for commit message
        commit_msg = commit_message.split("\n")[0]
        files_to_commit = [
            str(generated_file_path),
            str(dispatcher.output_path / "refactored_tab.py"),
            str(dispatcher.output_path / "test_*.py")
        ]
        if dispatcher.git_commit_changes(commit_msg, files_to_commit):
            logger.info(f"Changes committed: {commit_msg}")
        else:
            logger.warning("Failed to commit changes")