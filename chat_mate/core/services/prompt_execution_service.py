import asyncio
import json
import logging
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, Union, List

from core.DriverManager import DriverManager
from core.services.git_integration_service import GitIntegrationService
from core.PathManager import PathManager
from config.ConfigManager import ConfigManager
from core.executors.cursor_executor import CursorExecutor
from core.executors.chatgpt_executor import ChatGPTExecutor


class ModelType(Enum):
    """Supported model types for prompt execution."""
    CURSOR = "cursor"
    CHATGPT = "chatgpt"


class PromptExecutionService:
    """
    Centralized service for executing prompts across different models and managing project context.
    It supports:
      - Prompt execution via different executors (Cursor or ChatGPT).
      - Post-execution tasks such as test running and git integration.
      - Loading (and optionally auto-generating) project context from project_analysis.json.
    """

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        path_manager: Optional[PathManager] = None,
        logger: Optional[logging.Logger] = None,
        auto_generate_if_missing: bool = False
    ) -> None:
        """
        Initialize the PromptExecutionService.

        Args:
            config_manager (Optional[ConfigManager]): Configuration manager instance.
            path_manager (Optional[PathManager]): Path manager for file operations.
            logger (Optional[logging.Logger]): Optional logger instance.
            auto_generate_if_missing (bool): If True, auto-scan the project directory when project_analysis.json is missing.
        """
        self.config = config_manager
        self.path_manager = path_manager
        self.logger = logger or logging.getLogger(__name__)
        self.auto_generate_if_missing = auto_generate_if_missing
        self.project_context_cache: Optional[Dict[str, Any]] = None

        # Initialize managers and services if config_manager and path_manager are provided.
        if self.config and self.path_manager:
            self.driver_manager = DriverManager(self.config)
            self.git_service = GitIntegrationService(self.path_manager)
            self.cursor_executor = CursorExecutor(self.config, self.path_manager)
            self.chatgpt_executor = ChatGPTExecutor(self.driver_manager, self.config, self.path_manager)
        else:
            self.driver_manager = None
            self.git_service = None
            self.cursor_executor = None
            self.chatgpt_executor = None

    async def execute_prompt(
        self,
        prompt: str,
        model_type: ModelType,
        test_file: Optional[str] = None,
        generate_tests: bool = False,
        auto_commit: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a prompt using the specified model and handle post-execution tasks.

        Args:
            prompt (str): The prompt text to execute.
            model_type (ModelType): Which model to use (CURSOR or CHATGPT).
            test_file (Optional[str]): Optional path to a test file.
            generate_tests (bool): Whether to generate tests.
            auto_commit (bool): Whether to auto-commit changes.
            **kwargs: Additional model-specific parameters.

        Returns:
            Dict[str, Any]: Dictionary containing execution result details.
        """
        try:
            executor = self._get_executor(model_type)
            result = await executor.execute(
                prompt=prompt,
                test_file=test_file,
                generate_tests=generate_tests,
                **kwargs
            )
            if not result.get("success", False):
                return result

            await self._handle_post_execution(result, auto_commit, test_file, **kwargs)
            return result

        except Exception as e:
            self.logger.error(f"Error executing prompt: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "response": "",
                "artifacts": {}
            }

    def archive_files(self, files: Union[str, List[str]], destination: str) -> bool:
        """
        Archive specified files to the archive directory.

        Args:
            files (Union[str, List[str]]): Single file path or list of file paths to archive.
            destination (str): Destination subdirectory within the archive.

        Returns:
            bool: True if archiving was successful; False otherwise.
        """
        try:
            file_list = [files] if isinstance(files, str) else files
            archive_path = self.path_manager.get_archive_path(destination)
            archive_path.mkdir(parents=True, exist_ok=True)

            for file_path in file_list:
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

    async def _handle_post_execution(
        self,
        result: Dict[str, Any],
        auto_commit: bool,
        test_file: Optional[str],
        **kwargs
    ) -> None:
        """Handle post-execution tasks like running tests and committing changes via git."""
        try:
            if test_file and result.get("success", False):
                test_result = await self._run_tests(test_file)
                result["test_results"] = test_result
                result["success"] = result["success"] and test_result.get("success", False)

            if auto_commit and result.get("success", False) and self.git_service:
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
            test_file (str): Path to the test file.

        Returns:
            Dict[str, Any]: Dictionary containing test results.
        """
        try:
            from core.testing.test_runner import TestRunner
            runner = TestRunner(self.path_manager)
            return await runner.run_tests(test_file)
        except Exception as e:
            self.logger.error(f"Error running tests: {str(e)}")
            return {"success": False, "error": str(e)}

    def _get_executor(self, model_type: ModelType) -> Any:
        """
        Retrieve the appropriate executor based on the model type.

        Args:
            model_type (ModelType): The selected model type.

        Returns:
            Executor instance corresponding to the model type.
        """
        if model_type == ModelType.CURSOR:
            if not self.cursor_executor:
                raise ValueError("Cursor executor is not initialized.")
            return self.cursor_executor
        elif model_type == ModelType.CHATGPT:
            if not self.chatgpt_executor:
                raise ValueError("ChatGPT executor is not initialized.")
            return self.chatgpt_executor
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

    def load_project_context(self, project_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        Load project context from project_analysis.json in the specified directory.
        Optionally auto-generates the file if missing.

        Args:
            project_dir (Optional[Union[str, Path]]): Base directory to scan (defaults to current working directory).

        Returns:
            Dict[str, Any]: The loaded project context, or an empty dict if not found.
        """
        try:
            # Resolve project directory
            base_dir = Path(project_dir) if isinstance(project_dir, str) else project_dir or Path.cwd()
            context_path = base_dir / "project_analysis.json"

            if not context_path.exists():
                self.logger.warning(f"project_analysis.json not found at {context_path}")
                if self.auto_generate_if_missing:
                    self.logger.info("AutoScan enabled: Triggering project scan...")
                    from core.ProjectScanner import ProjectScanner
                    scanner = ProjectScanner(project_dir=base_dir)
                    scanner.scan()  # Should generate project_analysis.json
                    if not context_path.exists():
                        self.logger.error("Project scan did not produce project_analysis.json")
                        return {}
                    self.logger.info("Project scan complete. Reloading context...")
                else:
                    return {}

            with context_path.open("r", encoding="utf-8") as f:
                self.project_context_cache = json.load(f)
                self.logger.info(f"Loaded project context from {context_path}")
                return self.project_context_cache

        except Exception as e:
            self.logger.error(f"Failed to load project context: {str(e)}")
            return {}

    def clear_context_cache(self) -> None:
        """Clear the cached project context."""
        self.project_context_cache = None

    def shutdown(self) -> None:
        """Perform a clean shutdown of the service and its components."""
        try:
            if self.driver_manager:
                self.driver_manager.shutdown()
            if self.cursor_executor:
                self.cursor_executor.shutdown()
            if self.chatgpt_executor:
                self.chatgpt_executor.shutdown()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")
