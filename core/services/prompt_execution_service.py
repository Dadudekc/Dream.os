import asyncio
import json
import logging
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, Union, List

from PyQt5.QtCore import QObject, pyqtSignal
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

# Project-specific imports (ensure these modules are in your PYTHONPATH)
from core.DriverManager import DriverManager
from core.services.git_integration_service import GitIntegrationService
from core.PathManager import PathManager
from config.ConfigManager import ConfigManager
from core.executors.cursor_executor import CursorExecutor
from core.executors.chatgpt_executor import ChatGPTExecutor
from core.services.discord.DiscordBatchDispatcher import DiscordBatchDispatcher
from core.ReinforcementEvaluator import ReinforcementEvaluator
from core.DriverSessionManager import DriverSessionManager
from core.services.config_service import ConfigService


class ModelType(Enum):
    """Supported model types for prompt execution."""
    CURSOR = "cursor"
    CHATGPT = "chatgpt"


class UnifiedPromptService(QObject):
    """
    A unified prompt service that combines:
      - Asynchronous prompt execution via ChatGPT and Cursor executors,
      - Synchronous prompt cycles using Selenium (with both sequential and concurrent flows),
      - Orchestration for multi–prompt async execution, Discord feedback, and reinforcement evaluation,
      - Prompt management (caching, saving, resetting),
      - Project context loading and file archiving,
      - Coordinated shutdown of all components.
    """
    log_message = pyqtSignal(str)

    def __init__(
        self,
        config_manager: ConfigManager,
        path_manager: PathManager,
        config_service: ConfigService,
        prompt_manager: Any,
        driver_manager: DriverManager,
        feedback_engine: Optional[Any] = None,
        auto_generate_if_missing: bool = False,
        model: str = "gpt-4o-mini",
        cycle_speed: int = 2,
        stable_wait: int = 10
    ) -> None:
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Core dependencies
        self.config = config_manager
        self.path_manager = path_manager
        self.config_service = config_service
        self.prompt_manager = prompt_manager
        self.driver_manager = driver_manager
        self.feedback_engine = feedback_engine
        self.auto_generate_if_missing = auto_generate_if_missing

        # Async executors & integrations (for code generation and git integration)
        # Extract configuration values instead of passing the entire config_manager object
        headless = getattr(self.config, "headless", True) if not hasattr(self.config, "get") else self.config.get("headless", True)
        profile_dir = getattr(self.config, "profile_dir", None) if not hasattr(self.config, "get") else self.config.get("profile_dir", None)
        cookie_file = getattr(self.config, "cookie_file", None) if not hasattr(self.config, "get") else self.config.get("cookie_file", None)
        chrome_options = getattr(self.config, "chrome_options", []) if not hasattr(self.config, "get") else self.config.get("chrome_options", [])
        
        self.driver_manager_instance = DriverManager(
            headless=headless,
            profile_dir=profile_dir,
            cookie_file=cookie_file,
            undetected_mode=True,
            additional_arguments=chrome_options,
            timeout=30
        )
        self.git_service = GitIntegrationService(self.path_manager)
        self.cursor_executor = CursorExecutor(self.config, self.path_manager)
        self.chatgpt_executor = ChatGPTExecutor(self.driver_manager_instance, self.config, self.path_manager)

        # Orchestration components (for multi–prompt async execution, Discord, and reinforcement learning)
        # Use delayed import to avoid circular dependencies
        try:
            # Late import to avoid circular dependency
            from core.PromptCycleOrchestrator import PromptCycleOrchestrator
            self.orchestrator = PromptCycleOrchestrator(self.config_service)
        except ImportError:
            self.logger.warning("PromptCycleOrchestrator not imported due to circular dependency. Will initialize later if needed.")
            self.orchestrator = None
            
        self.discord_dispatcher = DiscordBatchDispatcher(self.config_service)
        self.evaluator = ReinforcementEvaluator(self.config_service)
        self.driver_session_manager = DriverSessionManager(self.config_service)

        # Start any required background services
        self.discord_dispatcher.start()

        # Synchronous (Selenium-based) prompt execution settings
        self.model = model
        self.cycle_speed = cycle_speed
        self.stable_wait = stable_wait

        # Caches
        self.project_context_cache: Optional[Dict[str, Any]] = None
        self.prompt_cache: Dict[str, str] = {}

        self.logger.info("UnifiedPromptService initialized successfully.")

    # -------------------------------------------------
    # ASYNCHRONOUS PROMPT EXECUTION (Generators via Executors)
    # -------------------------------------------------
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
        Execute a prompt asynchronously using the selected executor.
        Performs post-execution tasks (test running, git commit) if enabled.

        Returns:
            A dictionary with execution details.
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

    def _get_executor(self, model_type: ModelType) -> Any:
        """
        Retrieve the appropriate executor based on the model type.
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

    async def _handle_post_execution(
        self,
        result: Dict[str, Any],
        auto_commit: bool,
        test_file: Optional[str],
        **kwargs
    ) -> None:
        """
        Handle tasks following prompt execution such as running tests and git commits.
        """
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
        Run tests using the specified test file.
        """
        try:
            from core.testing.test_runner import TestRunner
            runner = TestRunner(self.path_manager)
            return await runner.run_tests(test_file)
        except Exception as e:
            self.logger.error(f"Error running tests: {str(e)}")
            return {"success": False, "error": str(e)}

    # -------------------------------------------------
    # SYNCHRONOUS PROMPT EXECUTION (Selenium–Based Cycles)
    # -------------------------------------------------
    def execute_prompt_cycle(self, prompt_text: str) -> str:
        """
        Execute a single prompt cycle synchronously:
         - Send the prompt,
         - Wait for response stabilization,
         - Optionally post-process and update feedback.
        """
        self.logger.info(f"Executing prompt cycle using model '{self.model}'...")
        if not self.send_prompt(prompt_text):
            self.logger.error("Failed to send prompt")
            return ""

        wait_time = self._determine_wait_time()
        self.logger.info(f"⏳ Waiting {wait_time} seconds for response stabilization...")
        time.sleep(wait_time)

        response = self._fetch_response()
        if response and "jawbone" in self.model.lower():
            response = self._post_process_jawbone_response(response)

        if not response:
            self.logger.warning("No response detected after sending prompt.")
        else:
            self.logger.info(f"Response received. Length: {len(response)} characters.")

        if self.feedback_engine:
            memory_update = self.feedback_engine.parse_and_update_memory(response)
            if memory_update:
                self.logger.info(f"🧠 Memory updated: {memory_update}")

        return response

    def execute_prompts_single_chat(self, prompt_list: List[str]) -> List[Dict[str, str]]:
        """
        Execute a list of prompts sequentially on a single chat.
        """
        self.logger.info(f"Starting sequential prompt execution on a single chat ({len(prompt_list)} prompts)...")
        responses = []

        for prompt_name in prompt_list:
            prompt_text = self.get_prompt(prompt_name)
            self.logger.info(f"Sending prompt: {prompt_name}")
            response = self.execute_prompt_cycle(prompt_text)
            responses.append({
                "prompt_name": prompt_name,
                "response": response
            })
            time.sleep(self.cycle_speed)

        self.logger.info("Sequential prompt cycle complete.")
        return responses

    def execute_prompts_concurrently(self, chat_link: str, prompt_list: List[str]) -> None:
        """
        Execute a list of prompts concurrently on a single chat using threads.
        """
        self.logger.info(f"Executing {len(prompt_list)} prompts concurrently on chat: {chat_link}")
        threads = []
        driver: Optional[WebDriver] = self.driver_manager.get_driver()
        if driver:
            driver.get(chat_link)
            time.sleep(2)

        for prompt_name in prompt_list:
            thread = threading.Thread(
                target=self._execute_single_prompt_thread,
                args=(chat_link, prompt_name)
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.logger.info("All prompt executions completed concurrently.")

    def _execute_single_prompt_thread(self, chat_link: str, prompt_name: str) -> None:
        """
        Thread target: execute a single prompt cycle.
        """
        self.logger.info(f"[Thread] Executing prompt '{prompt_name}' on chat {chat_link}")
        prompt_text = self.get_prompt(prompt_name)
        response = self.execute_prompt_cycle(prompt_text)
        if not response:
            self.logger.warning(f"[Thread] No response for prompt '{prompt_name}' on chat {chat_link}")
            return
        if self.feedback_engine:
            memory_update = self.feedback_engine.parse_and_update_memory(response)
            if memory_update:
                self.logger.info(f"🧠 [Thread] Memory updated: {memory_update}")
        self.logger.info(f"[Thread] Completed prompt '{prompt_name}' on chat {chat_link}")

    def _determine_wait_time(self) -> int:
        """
        Determine dynamic wait time based on model.
        """
        if "mini" in self.model.lower():
            return 5
        elif "jawbone" in self.model.lower():
            return 15
        else:
            return self.stable_wait

    def _post_process_jawbone_response(self, response: str) -> str:
        """
        Post-process responses for models like Jawbone.
        """
        self.logger.info("Post-processing Jawbone response...")
        return response.replace("[Start]", "").replace("[End]", "").strip()

    def send_prompt(self, prompt_text: str) -> bool:
        """
        Locate the chat input field and send the prompt.
        """
        self.logger.info("Locating input field to send prompt...")
        driver: Optional[WebDriver] = self.driver_manager.get_driver()
        if not driver:
            self.logger.error("Driver not initialized")
            return False

        try:
            input_box = driver.find_element(By.XPATH, "//textarea[@data-id='root-textarea']")
            input_box.clear()
            input_box.send_keys(prompt_text)
            time.sleep(1)
            send_button = driver.find_element(By.XPATH, "//button[@data-testid='send-button']")
            send_button.click()
            self.logger.info("Prompt sent successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send prompt: {e}")
            return False

    def _fetch_response(self) -> str:
        """
        Retrieve the latest AI response from the chat.
        """
        self.logger.info("Fetching latest response...")
        driver: Optional[WebDriver] = self.driver_manager.get_driver()
        if not driver:
            self.logger.error("Driver not initialized")
            return ""

        try:
            time.sleep(2)
            response_blocks = driver.find_elements(By.CSS_SELECTOR, 'div[data-message-author-role="assistant"]')
            if not response_blocks:
                self.logger.warning("No response blocks found.")
                return ""
            latest_response = response_blocks[-1]
            response_text = latest_response.text.strip()
            # Check if response is still streaming
            is_complete = not driver.find_elements(By.CSS_SELECTOR, '.result-streaming')
            if not is_complete:
                self.logger.info("Response is still streaming, waiting...")
                time.sleep(3)
                response_blocks = driver.find_elements(By.CSS_SELECTOR, 'div[data-message-author-role="assistant"]')
                if response_blocks:
                    response_text = response_blocks[-1].text.strip()
            self.logger.info(f"Response fetched. Length: {len(response_text)} characters")
            return response_text
        except Exception as e:
            self.logger.error(f"Error fetching response: {e}")
            return ""

    def wait_for_stable_response(self, max_wait: Optional[int] = None) -> str:
        """
        Wait until the AI response stabilizes (stops changing).
        """
        max_wait = max_wait or self.stable_wait
        self.logger.info(f"Waiting for stable response (max {max_wait}s)...")
        driver: Optional[WebDriver] = self.driver_manager.get_driver()
        if not driver:
            self.logger.error("Driver not initialized")
            return ""

        try:
            last_response = ""
            stable_time = 0
            start_time = time.time()

            while time.time() - start_time < max_wait:
                current_response = self._fetch_response()
                if current_response == last_response and current_response:
                    stable_time += 1
                    if stable_time >= 3:
                        self.logger.info("Response has stabilized.")
                        return current_response
                else:
                    stable_time = 0
                    last_response = current_response
                time.sleep(1)
            self.logger.warning("Max wait time exceeded, returning current response.")
            return last_response
        except Exception as e:
            self.logger.error(f"Error waiting for stable response: {e}")
            return ""

    # -------------------------------------------------
    # ASYNCHRONOUS ORCHESTRATION & PROMPT MANAGEMENT
    # -------------------------------------------------
    async def execute_prompt_async_orchestrated(self, prompt_text: str, new_chat: bool = False) -> List[str]:
        """
        Execute a prompt asynchronously via the orchestrator.
        Emits log messages for feedback and queues Discord messages if enabled.
        """
        if not prompt_text:
            self.log_message.emit("No prompt text provided.")
            return []

        try:
            responses = await self.orchestrator.execute_single_cycle_async(prompt_text, new_chat)
            for response in responses:
                evaluation = self.evaluator.evaluate_response(response, prompt_text)
                self.log_message.emit(f"Response evaluation: {evaluation['feedback']}")
                if self.config_service.get('DISCORD_FEEDBACK_ENABLED', False):
                    await self.discord_dispatcher.queue_message_async(
                        self.config_service.get('DISCORD_CHANNEL_ID'),
                        f"Feedback for prompt: {evaluation['feedback']}"
                    )
            return responses
        except Exception as e:
            self.logger.error(f"Error executing prompt asynchronously: {str(e)}", exc_info=True)
            self.log_message.emit(f"Error executing prompt: {str(e)}")
            return []

    async def execute_multi_prompt_async(self, prompts: List[str], reverse_order: bool = False) -> Dict[str, List[str]]:
        """
        Execute multiple prompts asynchronously across chats.
        Returns a mapping from chat titles to their responses.
        """
        if not prompts:
            self.log_message.emit("No prompts provided.")
            return {}

        try:
            results = await self.orchestrator.execute_multi_cycle_async(prompts, reverse_order)
            for chat_title, responses in results.items():
                for response in responses:
                    evaluation = self.evaluator.evaluate_response(response, prompts[0])
                    self.log_message.emit(f"Chat {chat_title} response evaluation: {evaluation['feedback']}")
                    if self.config_service.get('DISCORD_FEEDBACK_ENABLED', False):
                        await self.discord_dispatcher.queue_message_async(
                            self.config_service.get('DISCORD_CHANNEL_ID'),
                            f"Chat {chat_title} feedback: {evaluation['feedback']}"
                        )
            return results
        except Exception as e:
            self.logger.error(f"Error executing multi-prompt asynchronously: {str(e)}", exc_info=True)
            self.log_message.emit(f"Error executing multi-prompt: {str(e)}")
            return {}

    def get_prompt_insights(self, prompt_text: str) -> Dict[str, Any]:
        """
        Retrieve insights for the given prompt.
        """
        return self.evaluator.get_prompt_insights(prompt_text)

    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Get a summary of stored memory data.
        """
        return self.evaluator.get_memory_summary()

    def save_prompt(self, prompt_type: str, prompt_text: str) -> bool:
        """
        Save a prompt and update the cache.
        """
        success = self.orchestrator.save_prompt(prompt_type, prompt_text)
        if success:
            self.prompt_cache[prompt_type] = prompt_text
        return success

    def reset_prompts(self) -> bool:
        """
        Reset prompts to their defaults.
        """
        return self.orchestrator.reset_prompts()

    def get_available_prompts(self) -> List[str]:
        """
        Retrieve a list of available prompt types.
        """
        if not self.prompt_cache:
            self.prompt_cache = self.orchestrator.get_available_prompts()
        return list(self.prompt_cache.keys())

    def get_prompt(self, prompt_type: str) -> str:
        """
        Get the prompt text for a specific prompt type.
        """
        if prompt_type in self.prompt_cache:
            return self.prompt_cache[prompt_type]
        prompt_text = self.orchestrator.get_prompt(prompt_type)
        self.prompt_cache[prompt_type] = prompt_text
        return prompt_text

    # -------------------------------------------------
    # PROJECT CONTEXT & FILE ARCHIVING
    # -------------------------------------------------
    def _load_project_context(self, filepath: Union[str, Path, ConfigManager]) -> Optional[Dict[str, Any]]:
        """
        Load project context from a JSON file or ConfigManager.
        
        Args:
            filepath: Path to the context file or a ConfigManager instance
            
        Returns:
            Dict with context data or None if loading failed
        """
        try:
            # Handle ConfigManager instances by extracting their context_file_path property
            if isinstance(filepath, ConfigManager):
                # Extract the path from ConfigManager using get method if available
                if hasattr(filepath, 'get'):
                    filepath_str = filepath.get("context_file_path", "")
                else:
                    # Try accessing as an attribute if get method isn't available
                    filepath_str = getattr(filepath, "context_file_path", "")
                
                # If we couldn't get a path from the ConfigManager, use a default
                if not filepath_str:
                    self.logger.warning("No context file path found in ConfigManager")
                    filepath_str = str(self.path_manager.get_path("memory", "project_context.json"))
            else:
                # Convert to string if it's a Path object or already a string
                filepath_str = str(filepath)
                
            if not filepath_str:
                self.logger.warning("No context file path provided")
                return None
                
            context_path = Path(filepath_str)
            if not context_path.exists():
                self.logger.warning(f"Context file does not exist: {context_path}")
                return None
                
            with open(context_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load project context: {e}")
            return None

    def load_project_context(self, project_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        Load project context from project_analysis.json.
        Optionally auto-generates the file if missing and auto-generation is enabled.
        """
        try:
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

    def archive_files(self, files: Union[str, List[str]], destination: str) -> bool:
        """
        Archive one or more files into a designated archive subdirectory.
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

    def clear_context_cache(self) -> None:
        """Clear the cached project context."""
        self.project_context_cache = None

    # -------------------------------------------------
    # SHUTDOWN & RESOURCE CLEANUP
    # -------------------------------------------------
    def shutdown(self) -> None:
        """
        Cleanly shut down all components and background services.
        """
        try:
            if self.driver_manager_instance:
                self.driver_manager_instance.shutdown()
            if self.cursor_executor:
                self.cursor_executor.shutdown()
            if self.chatgpt_executor:
                self.chatgpt_executor.shutdown()
            if self.discord_dispatcher:
                self.discord_dispatcher.stop()
            if self.driver_manager:
                self.driver_manager.shutdown_driver()
            self.log_message.emit("UnifiedPromptService shutdown complete.")
            self.logger.info("UnifiedPromptService successfully shut down.")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")
