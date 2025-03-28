"""Backend service for managing Cursor execution and related operations."""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from core.refactor.cursor_dispatcher import CursorDispatcher

class CursorExecutionService:
    """Backend service for managing Cursor execution, templates, sequences, and Git operations."""
    
    def __init__(self, config_service: Any, logger: Optional[logging.Logger] = None):
        """
        Initialize the CursorExecutionService.
        
        Args:
            config_service: Configuration service instance
            logger: Optional logger instance
        """
        self.config = config_service
        self.logger = logger or logging.getLogger(__name__)
        self.dispatcher = CursorDispatcher()

    def get_available_templates(self) -> List[str]:
        """Get list of available template names."""
        try:
            templates_path = self.dispatcher.templates_path
            return [f.name for f in templates_path.glob("*.j2")]
        except Exception as e:
            self.logger.error(f"Error loading templates: {e}")
            return []

    def get_available_sequences(self) -> List[str]:
        """Get list of available sequence names."""
        try:
            sequences_path = self.dispatcher.templates_path.parent / "sequences"
            if not sequences_path.exists():
                return []
            return [f.stem for f in sequences_path.glob("*.json")]
        except Exception as e:
            self.logger.error(f"Error loading sequences: {e}")
            return []

    def get_sequence_info(self, sequence_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific sequence.
        
        Args:
            sequence_name: Name of the sequence
            
        Returns:
            Dict containing sequence information or None if not found
        """
        try:
            sequence_path = self.dispatcher.templates_path.parent / "sequences" / f"{sequence_name}.json"
            if not sequence_path.exists():
                return None
                
            with open(sequence_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading sequence info: {e}")
            return None

    def execute_prompt(self, 
                      template_name: str, 
                      context: Dict[str, Any],
                      initial_code: str = "",
                      skip_wait: bool = False,
                      run_tests: bool = True) -> Tuple[bool, str, Optional[str]]:
        """
        Execute a single prompt through Cursor.
        
        Args:
            template_name: Name of the template to use
            context: Context variables for template rendering
            initial_code: Initial code to start with
            skip_wait: Whether to skip waiting for user input
            run_tests: Whether to run tests after execution
            
        Returns:
            Tuple of (success, result_code, error_message)
        """
        try:
            # Render template
            prompt_text = self.dispatcher.run_prompt(template_name, context)
            
            # Send to Cursor and wait for edit
            code_result = self.dispatcher.send_and_wait(initial_code, prompt_text, skip_wait=skip_wait)
            
            # Run tests if enabled
            test_result = None
            if run_tests:
                code_file = self.dispatcher.output_path / "generated_tab.py"
                test_success, test_output = self.dispatcher.run_tests(str(code_file))
                if not test_success:
                    return False, code_result, f"Tests failed: {test_output}"
            
            return True, code_result, None
            
        except Exception as e:
            self.logger.error(f"Error executing prompt: {e}")
            return False, "", str(e)

    def execute_sequence(self, 
                        sequence_name: str, 
                        initial_context: Dict[str, Any],
                        skip_wait: bool = False) -> Tuple[bool, str, Optional[str]]:
        """
        Execute a sequence of prompts.
        
        Args:
            sequence_name: Name of the sequence to execute
            initial_context: Initial context for the sequence
            skip_wait: Whether to skip waiting for user input
            
        Returns:
            Tuple of (success, final_code, error_message)
        """
        try:
            final_code = self.dispatcher.execute_prompt_sequence(
                sequence_name, 
                initial_context, 
                skip_wait=skip_wait
            )
            return True, final_code, None
        except Exception as e:
            self.logger.error(f"Error executing sequence: {e}")
            return False, "", str(e)

    def generate_tests(self, file_path: str) -> Tuple[bool, str, Optional[str]]:
        """
        Generate tests for a given file.
        
        Args:
            file_path: Path to the file to test
            
        Returns:
            Tuple of (success, test_file_path, error_message)
        """
        try:
            code_path = Path(file_path)
            if not code_path.exists():
                return False, "", f"File not found: {file_path}"
                
            test_file_path = self.dispatcher.output_path / f"test_{code_path.stem}.py"
            self.dispatcher._create_test_file(file_path, str(test_file_path))
            
            return True, str(test_file_path), None
        except Exception as e:
            self.logger.error(f"Error generating tests: {e}")
            return False, "", str(e)

    def run_tests(self, file_path: str) -> Tuple[bool, str, Optional[str]]:
        """
        Run tests for a given file.
        
        Args:
            file_path: Path to the file to test
            
        Returns:
            Tuple of (success, test_output, error_message)
        """
        try:
            code_path = Path(file_path)
            if not code_path.exists():
                return False, "", f"File not found: {file_path}"
                
            success, output = self.dispatcher.run_tests(file_path)
            return success, output, None
        except Exception as e:
            self.logger.error(f"Error running tests: {e}")
            return False, "", str(e)

    def install_git_hooks(self) -> Tuple[bool, Optional[str]]:
        """
        Install Git hooks.
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            success = self.dispatcher.install_git_hook("post-commit")
            return success, None
        except Exception as e:
            self.logger.error(f"Error installing Git hooks: {e}")
            return False, str(e)

    def commit_changes(self, commit_message: str, files: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Commit changes to Git.
        
        Args:
            commit_message: Commit message
            files: List of files to commit
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            success = self.dispatcher.git_commit_changes(commit_message, files)
            return success, None
        except Exception as e:
            self.logger.error(f"Error committing changes: {e}")
            return False, str(e)

    def shutdown(self):
        """Clean up resources."""
        if self.dispatcher:
            self.dispatcher.shutdown() 