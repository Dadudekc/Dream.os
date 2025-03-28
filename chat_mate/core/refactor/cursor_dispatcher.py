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
        timestamp_file.write_text(timestamp)
        return timestamp
        
    def load_and_render(self, template_name: str, context: Dict[str, str]) -> str:
        template_path = self.templates_path / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        raw_template = template_path.read_text()
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

        code_file.write_text(code_output)
        prompt_file.write_text(prompt_text)

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
                
            updated_content = file_path.read_text()
            logger.info(f"✅ Loaded code from {base_filename}.py")
            return updated_content
        except KeyboardInterrupt:
            logger.warning("Process interrupted by user.")
            raise
        except Exception as e:
            logger.error(f"Error loading generated code: {str(e)}")
            raise
            
    def send_and_wait(self, code_output: str, prompt_text: str, base_filename="generated_tab", skip_wait=False) -> str:
        """
        Combines send_to_cursor and wait_for_cursor_edit into a single operation.
        
        Args:
            code_output: Initial code to send to Cursor
            prompt_text: Prompt text to guide Cursor's editing
            base_filename: Base name for the files
            skip_wait: If True, skips waiting for user input
            
        Returns:
            The content of the file after user edits in Cursor (or immediately if skip_wait is True)
        """
        self.send_to_cursor(code_output, prompt_text, base_filename)
        return self.wait_for_cursor_edit(base_filename, skip_wait)
        
    def run_tests(self, code_file_path: str, test_file_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Executes tests for the generated code file.
        
        Args:
            code_file_path: Path to the code file to test
            test_file_path: Path to the test file (if None, will be auto-generated)
            
        Returns:
            A tuple of (success, output)
        """
        logger.info(f"🧪 Running tests for: {code_file_path}")
        
        if test_file_path is None:
            # Generate a test file name based on the code file
            code_path = Path(code_file_path)
            test_file_path = str(self.output_path / f"test_{code_path.stem}.py")
            
            # Check if we need to generate tests
            test_path = Path(test_file_path)
            if not test_path.exists():
                logger.info(f"Generating test file at: {test_file_path}")
                self._create_test_file(code_file_path, test_file_path)
        
        try:
            # Run the tests using unittest
            result = subprocess.run(
                ["python", "-m", "unittest", test_file_path],
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            output = result.stdout + "\n" + result.stderr
            success = (result.returncode == 0)
            
            if success:
                logger.info(f"✅ Tests PASSED for {code_file_path}")
            else:
                logger.warning(f"❌ Tests FAILED for {code_file_path}")
                logger.debug(f"Test output: {output}")
                
            # Create a structured test result for analysis
            test_results = {
                "success": success,
                "output": output,
                "file_tested": code_file_path,
                "test_file": test_file_path,
                "return_code": result.returncode
            }
            
            # Store results for later analysis
            results_file = self.output_path / "test_results.json"
            self._append_to_json(results_file, test_results)
                
            return success, output
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"❌ Timeout when running tests: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"❌ Exception when running tests: {e}")
            return False, str(e)
    
    def _create_test_file(self, code_file_path: str, test_file_path: str) -> None:
        """
        Creates a test file for the given code file using Cursor.
        
        Args:
            code_file_path: Path to the code file
            test_file_path: Path to create the test file
        """
        try:
            # Read the code file
            code_content = Path(code_file_path).read_text()
            
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
            
            # Save the generated test code
            Path(test_file_path).write_text(test_code)
            logger.info(f"✅ Generated test file: {test_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to create test file: {e}")
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
            Path(test_file_path).write_text(minimal_test)
            logger.info(f"⚠️ Created minimal test file: {test_file_path}")
    
    def _append_to_json(self, file_path: Path, data: dict) -> None:
        """
        Appends data to a JSON file, creating it if it doesn't exist.
        
        Args:
            file_path: Path to the JSON file
            data: Dictionary data to append
        """
        try:
            # Initialize with an empty list if file doesn't exist
            if not file_path.exists():
                file_path.write_text("[]")
                
            # Read existing data
            with open(file_path, 'r') as f:
                json_data = json.load(f)
                
            # Append new data
            json_data.append(data)
            
            # Write back to file
            with open(file_path, 'w') as f:
                json.dump(json_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to append data to {file_path}: {e}")
            # Still try to write current data if previous JSON was corrupted
            try:
                with open(file_path, 'w') as f:
                    json.dump([data], f, indent=2)
            except:
                logger.error(f"Could not salvage data for {file_path}")
                    
    def execute_prompt_sequence(self, sequence_name: str, initial_context: Dict, skip_wait=False):
        """
        Executes a sequence of prompts defined in a JSON configuration file.

        Args:
            sequence_name: Name or full path of the prompt sequence to execute
            initial_context: Initial context to start the sequence with
            skip_wait: If True, skips waiting for user input

        Returns:
            The final output of the sequence
        """
        # Allow full path or just a name
        sequence_path = Path(sequence_name)
        if not sequence_path.exists():
            sequence_path = self.templates_path / "sequences" / f"{sequence_name}.json"


        if not sequence_path.exists():
            logger.error(f"Prompt sequence not found: {sequence_name}")
            raise FileNotFoundError(f"Prompt sequence not found: {sequence_name}")

            
        try:
            with open(sequence_path, 'r') as f:
                sequence_data = json.load(f)
                
            logger.info(f"🔄 Starting prompt sequence: {sequence_name} with {len(sequence_data['steps'])} steps")
            
            # Initialize context with provided initial context
            context = initial_context.copy()
            current_code = sequence_data.get("initial_code", "# Code will be generated through the sequence")
            
            # Track results for each step
            sequence_results = {
                "sequence_name": sequence_name,
                "steps": [],
                "started_at": Path("timestamp.txt").read_text().strip() if Path("timestamp.txt").exists() else None,
                "context": context
            }
            
            # Process each step in the sequence
            for i, step in enumerate(sequence_data["steps"]):
                step_num = i + 1
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
                    updated_code = self.send_and_wait(current_code, prompt_text, output_file, skip_wait)
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
            with open(results_file, 'w') as f:
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
                               text=True)
            except subprocess.CalledProcessError:
                logger.error("Not inside a git repository.")
                return False
                
            # Add specified files
            files_str = " ".join(file_paths)
            add_cmd = f"git add {files_str}"
            logger.info(f"Adding files to git: {add_cmd}")
            subprocess.run(add_cmd, shell=True, check=True)
            
            # Create commit
            commit_cmd = f'git commit -m "{message}"'
            logger.info(f"Creating commit: {commit_cmd}")
            result = subprocess.run(commit_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Successfully committed changes: {message}")
                return True
            else:
                logger.error(f"Failed to commit changes: {result.stderr}")
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
    parser.add_argument("--auto", action="store_true", help="Run in automated mode, skipping user input pauses")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--sequence", help="Run a predefined prompt sequence instead of the default flow")
    parser.add_argument("--git-commit", action="store_true", help="Automatically commit changes at the end of the process")
    parser.add_argument("--install-hooks", action="store_true", help="Install Git hooks for analytics")
    # --------------------------
    # NEW ARG: Path to templates
    # --------------------------
    parser.add_argument(
        "--templates",
        type=str,
        default="D:/overnight_scripts/chat_mate/templates/prompt_templates",
        help="Path to the directory containing Jinja2 templates"
    )
    args = parser.parse_args()
    
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
            final_code = dispatcher.execute_prompt_sequence(args.sequence, initial_context, skip_wait=skip_waiting)
            
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
        code_result = dispatcher.send_and_wait(initial_code, raw_prompt_1, skip_wait=skip_waiting)
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
        test_success, test_output = dispatcher.run_tests(str(generated_file_path))
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
        refactored_result = dispatcher.send_and_wait(code_result, refactor_prompt, "refactored_tab", skip_wait=skip_waiting)
        print("\n--- Cursor Step 4 Output: Successfully refactored code ---")
        
        if run_tests:
            # Run tests on the refactored code
            refactored_file_path = dispatcher.output_path / "refactored_tab.py"
            refactor_test_success, refactor_test_output = dispatcher.run_tests(str(refactored_file_path))
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