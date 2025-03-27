import logging
from typing import Optional, Dict, Any, Union
from enum import Enum
from pathlib import Path
import asyncio

from core.DriverManager import DriverManager
from core.services.git_integration_service import GitIntegrationService
from core.PathManager import PathManager
from core.ConfigManager import ConfigManager
from core.executors.cursor_executor import CursorExecutor
from core.executors.chatgpt_executor import ChatGPTExecutor

class ModelType(Enum):
    """Supported model types for prompt execution."""
    CURSOR = "cursor"
    CHATGPT = "chatgpt"

class PromptExecutionService:
    """
    Centralized service for executing prompts across different models.
    Handles routing, execution, archiving, and optional test/git integration.
    """
    
    def __init__(self, 
                 config_manager: ConfigManager,
                 path_manager: PathManager,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the prompt execution service.
        
        Args:
            config_manager: Configuration manager instance
            path_manager: Path manager for file operations
            logger: Optional logger instance
        """
        self.config = config_manager
        self.path_manager = path_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize managers and services
        self.driver_manager = DriverManager(config_manager)
        self.git_service = GitIntegrationService(path_manager)
        
        # Initialize executors
        self.cursor_executor = CursorExecutor(config_manager, path_manager)
        self.chatgpt_executor = ChatGPTExecutor(
            self.driver_manager,
            config_manager,
            path_manager
        )
        
    async def execute_prompt(self,
                           prompt: str,
                           model_type: ModelType,
                           test_file: Optional[str] = None,
                           generate_tests: bool = False,
                           auto_commit: bool = False,
                           **kwargs) -> Dict[str, Any]:
        """
        Execute a prompt using the specified model.
        
        Args:
            prompt: The prompt text to execute
            model_type: Which model to use (CURSOR or CHATGPT)
            test_file: Optional path to test file
            generate_tests: Whether to generate tests
            auto_commit: Whether to auto-commit changes
            **kwargs: Additional model-specific parameters
            
        Returns:
            Dict containing:
                - success: bool
                - response: str
                - error: Optional[str]
                - artifacts: Dict[str, Any] (files created, tests generated, etc)
        """
        try:
            # Select executor based on model type
            executor = self._get_executor(model_type)
            
            # Execute the prompt
            result = await executor.execute(
                prompt=prompt,
                test_file=test_file,
                generate_tests=generate_tests,
                **kwargs
            )
            
            if not result["success"]:
                return result
                
            # Handle post-execution tasks
            await self._handle_post_execution(
                result=result,
                auto_commit=auto_commit,
                test_file=test_file,
                **kwargs
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing prompt: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "response": "",
                "artifacts": {}
            }
            
    def archive_files(self, files: Union[str, list[str]], destination: str) -> bool:
        """
        Archive specified files to the archive directory.
        
        Args:
            files: Single file path or list of file paths to archive
            destination: Destination directory within archive
            
        Returns:
            bool: True if archiving was successful
        """
        try:
            if isinstance(files, str):
                files = [files]
                
            archive_path = self.path_manager.get_archive_path(destination)
            archive_path.mkdir(parents=True, exist_ok=True)
            
            for file_path in files:
                src_path = Path(file_path)
                if not src_path.exists():
                    self.logger.warning(f"File not found: {file_path}")
                    continue
                    
                dest_path = archive_path / src_path.name
                src_path.rename(dest_path)
                self.logger.info(f"Archived {file_path} to {dest_path}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error archiving files: {str(e)}")
            return False
            
    async def _handle_post_execution(self,
                                   result: Dict[str, Any],
                                   auto_commit: bool,
                                   test_file: Optional[str],
                                   **kwargs) -> None:
        """Handle post-execution tasks like test running and git commits."""
        try:
            # Run tests if a test file was provided
            if test_file and result.get("success"):
                test_result = await self._run_tests(test_file)
                result["test_results"] = test_result
                
                # Update success based on test results
                result["success"] = result["success"] and test_result.get("success", False)
                
            # Handle git commit if requested and operation was successful
            if auto_commit and result.get("success"):
                commit_msg = kwargs.get("commit_message", "Auto-commit: Prompt execution changes")
                commit_result = await self.git_service.commit_changes(commit_msg)
                result["git_commit"] = commit_result
                
        except Exception as e:
            self.logger.error(f"Error in post-execution handling: {str(e)}")
            result["post_execution_error"] = str(e)
            
    async def _run_tests(self, test_file: str) -> Dict[str, Any]:
        """
        Run the specified test file.
        
        Args:
            test_file: Path to the test file to run
            
        Returns:
            Dict containing test results
        """
        try:
            # Import test runner dynamically to avoid circular imports
            from core.testing.test_runner import TestRunner
            
            runner = TestRunner(self.path_manager)
            return await runner.run_tests(test_file)
            
        except Exception as e:
            self.logger.error(f"Error running tests: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def _get_executor(self, model_type: ModelType):
        """Get the appropriate executor for the model type."""
        if model_type == ModelType.CURSOR:
            return self.cursor_executor
        elif model_type == ModelType.CHATGPT:
            return self.chatgpt_executor
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
            
    def shutdown(self):
        """Clean shutdown of the service and its components."""
        try:
            self.driver_manager.shutdown()
            self.cursor_executor.shutdown()
            self.chatgpt_executor.shutdown()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}") 