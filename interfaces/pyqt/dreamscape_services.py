import os
import json
import time
import logging
import threading
import re
from datetime import datetime, timedelta
import sys
import inspect
from typing import Optional

from pathlib import Path

def find_project_root(marker: str = ".git", start: Path = None) -> Path:
    """
    Recursively search for a directory containing the given marker (e.g., .git)
    starting from 'start' or the current file's directory.
    
    :param marker: A file or directory name that indicates the project root.
    :param start: Starting path for the search (defaults to current file's parent).
    :return: The project root as a Path object.
    """
    start = start or Path(__file__).resolve().parent
    for parent in [start] + list(start.parents):
        if (parent / marker).exists():
            return parent
    return start  # Fallback to start if no marker found

project_root = find_project_root()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# For debugging: print the project root
print("Project root detected at:", project_root)


from core.ChatManager import ChatManager
from core.AletheiaPromptManager import AletheiaPromptManager
from core.FileManager import FileManager
from core.UnifiedDiscordService import UnifiedDiscordService
from core.ReinforcementEngine import ReinforcementEngine
from utils.filesystem import sanitize_filename
from utils.run_summary import generate_full_run_json
from core.DriverManager import DriverManager
from core.CycleExecutionService import CycleExecutionService
from core.PromptResponseHandler import PromptResponseHandler
from core.services.discord.DiscordQueueProcessor import DiscordQueueProcessor
from core.TaskOrchestrator import TaskOrchestrator
from core.services.dreamscape.engine import DreamscapeGenerationService
from core.PromptCycleOrchestrator import PromptCycleOrchestrator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DreamscapeService:
    """
    Central service class that encapsulates all core business logic.
    This module has zero dependencies on any UI framework.
    
    Design rationale:
    - Centralizes all business logic and service creation
    - Provides robust error handling for all service initialization
    - Implements fallback mechanisms with EmptyService implementations
    - Supports runtime service creation and health checks
    """

    def __init__(self, config):
        """
        Initialize DreamscapeService with a configuration object.
        
        Args:
            config: A ConfigManager instance or configuration object that exposes settings.
        """
        self.config = config
        self.logger = logging.getLogger("DreamscapeService")
        
        # Track initialization status for health checks and debugging
        self._initialization_status = {}
        self._service_dependencies = self._map_service_dependencies()

        # Initialize service registry 
        self._services = {}
        
        # Bootstrap all services
        self.bootstrap_services()
        
        # Log initialization status
        self._log_initialization_status()
        self.logger.info("DreamscapeService initialized.")

    def _init_service(self, service_name, factory_func, dependencies=None):
        """
        Initialize a service using the provided factory function with error handling.
        
        Args:
            service_name: Name of the service
            factory_func: Function that creates the service
            dependencies: List of service names this service depends on
            
        Returns:
            The initialized service or an EmptyService if initialization fails
        """
        # Track start of initialization
        self._initialization_status[service_name] = "initializing"
        
        # Check dependencies first
        if dependencies:
            for dep in dependencies:
                dep_status = self._initialization_status.get(dep)
                if dep_status == "failed":
                    self.logger.warning(f"Dependency '{dep}' failed to initialize, {service_name} may not work correctly")
                elif dep_status is None or dep_status == "initializing":
                    self.logger.warning(f"Possible circular dependency detected: {service_name} depends on {dep}")
        
        try:
            service = factory_func()
            setattr(self, service_name, service)
            self._initialization_status[service_name] = "success"
            return service
        except Exception as e:
            self.logger.error(f"Failed to initialize {service_name}: {str(e)}")
            empty_service = self._create_empty_service(service_name)
            setattr(self, service_name, empty_service)
            self._initialization_status[service_name] = "failed"
            return empty_service

    def _init_discord_service(self):
        """
        Initialize the Discord service with appropriate parameters
        based on the constructor signature.
        """
        try:
            # Check which parameters the constructor accepts
            discord_params = inspect.signature(UnifiedDiscordService.__init__).parameters

            # Get appropriate parameters from config
            bot_token = self.config.get("discord_token", "") if hasattr(self.config, "get") else getattr(self.config, "discord_token", "")
            channel_id = self.config.get("discord_channel_id", "") if hasattr(self.config, "get") else getattr(self.config, "discord_channel_id", "")
            
            # Track initialization status
            self._initialization_status["discord"] = "initializing"
            
            # Initialize with the correct parameter set
            if 'config' in discord_params and 'logger' in discord_params:
                self.discord = UnifiedDiscordService(config=self.config, logger=self.logger)
            elif 'bot_token' in discord_params and 'default_channel_id' in discord_params:
                template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates", "discord_templates")
                self.discord = UnifiedDiscordService(
                    bot_token=bot_token, 
                    default_channel_id=channel_id,
                    template_dir=template_dir
                )
            else:
                # Fallback to default constructor
                self.discord = UnifiedDiscordService()
                
            self._initialization_status["discord"] = "success"
        except Exception as e:
            self.logger.error(f"Failed to initialize Discord service: {str(e)}")
            self.discord = self._create_empty_service("discord")
            self._initialization_status["discord"] = "failed"

    def _init_task_orchestrator(self):
        """
        Initialize the task orchestrator and configure it with the cycle service.
        """
        orchestrator = TaskOrchestrator(self.logger)
        orchestrator.set_cycle_service(self.cycle_service)
        return orchestrator

    def _create_empty_service(self, service_name):
        """
        Create an empty service object that can be safely used when a real service is unavailable.
        This prevents NoneType errors by providing stub implementations of common methods.
        
        Args:
            service_name: Name of the service to create an empty implementation for
            
        Returns:
            An object with stub methods that logs warnings when called
        """
        class EmptyService:
            def __init__(self, name):
                self.service_name = name
                self.logger = logging.getLogger(f"EmptyService.{name}")
                
            def __getattr__(self, name):
                def method(*args, **kwargs):
                    self.logger.warning(f"Call to unavailable service '{self.service_name}.{name}()'. Service not initialized.")
                    return None
                return method
                
            def is_empty_service(self):
                """Method to identify this as an empty service stub."""
                return True
        
        return EmptyService(service_name)
        
    def _map_service_dependencies(self):
        """
        Build a map of service dependencies for debugging and health checks.
        
        Returns:
            dict: A mapping of service dependencies.
        """
        # Simple dependency map for core services
        return {
            "cycle_service": ["prompt_manager", "chat_manager", "prompt_handler", "discord"],
            "task_orchestrator": ["cycle_service"],
            "dreamscape_generator": ["prompt_handler", "discord"]
        }
        
    def get_service(self, name):
        """
        Get a service by name from the service registry.
        
        Args:
            name: Name of the service to retrieve
            
        Returns:
            The requested service or None if not found
        """
        if not hasattr(self, "_services"):
            self._services = {}
        return self._services.get(name)
    
    def set_service(self, name, service):
        """
        Set a service in the service registry.
        
        Args:
            name: Name to register the service under
            service: The service instance to register
        """
        if not hasattr(self, "_services"):
            self._services = {}
        self._services[name] = service
        
    def _log_initialization_status(self):
        """
        Log the initialization status of all services for troubleshooting.
        """
        self.logger.info("Service initialization status:")
        for service, status in self._initialization_status.items():
            self.logger.info(f"  - {service}: {status}")
            
    def service_health_check(self):
        """
        Perform a health check on all services and return a status report.
        
        Returns:
            Dictionary with service status information
        """
        health_report = {}
        
        for service_name in self._initialization_status.keys():
            service = getattr(self, service_name, None)
            
            # Skip chat_manager if it's deferred
            if service_name == "chat_manager" and self._initialization_status.get(service_name) == "deferred":
                health_report[service_name] = {
                    "status": "deferred",
                    "message": "Will be initialized on demand"
                }
                continue
                
            if service is None:
                health_report[service_name] = {
                    "status": "not_found",
                    "message": "Service reference is None"
                }
            elif hasattr(service, "is_empty_service") and service.is_empty_service():
                health_report[service_name] = {
                    "status": "empty_implementation",
                    "message": "Using fallback implementation"
                }
            else:
                health_report[service_name] = {
                    "status": "available",
                    "message": "Service is available"
                }
                
        return health_report

    def shutdown(self):
        """
        Shutdown all services in the correct order.
        """
        # Ordered list of services to shut down (reverse dependency order)
        shutdown_order = [
            "dreamscape_generator",
            "task_orchestrator",
            "cycle_service",
            "chat_manager",
            "discord",
            "discord_processor"
        ]
        
        for service_name in shutdown_order:
            service = getattr(self, service_name, None)
            if service is None:
                continue
                
            # Try different shutdown method names
            for method_name in ["shutdown", "stop", "close", "cleanup"]:
                if hasattr(service, method_name) and callable(getattr(service, method_name)):
                    try:
                        self.logger.info(f"Shutting down {service_name}...")
                        getattr(service, method_name)()
                        break
                    except Exception as e:
                        self.logger.error(f"Error shutting down {service_name}: {str(e)}")

    # --- Chat Manager & Prompt Execution ---

    def create_chat_manager(self, model: str = None, headless: bool = None, excluded_chats: list = None,
                            timeout: int = 180, stable_period: int = 10, poll_interval: int = 5) -> None:
        """
        Create (or re-create) a ChatManager instance using provided or configuration defaults.
        """
        if self.chat_manager:
            self.chat_manager.shutdown_driver()

        model = model or self.config.default_model
        headless = headless if headless is not None else self.config.headless
        excluded_chats = excluded_chats or self.config.excluded_chats

        # Create driver options
        driver_options = {
            "headless": headless,
            "window_size": (1920, 1080),
            "disable_gpu": True,
            "no_sandbox": True,
            "disable_dev_shm": True
        }

        self.chat_manager = ChatManager(
            driver_options=driver_options,
            excluded_chats=excluded_chats,
            model=model,
            timeout=timeout,
            stable_period=stable_period,
            poll_interval=poll_interval,
            headless=headless
        )
        self.logger.info("ChatManager created with model '%s' and headless=%s", model, headless)

    def execute_prompt(self, prompt_text: str) -> list:
        """
        Execute a single prompt using the current ChatManager.
        
        :param prompt_text: The prompt text to execute.
        :return: A list of AI responses.
        """
        if not self.chat_manager:
            raise RuntimeError("ChatManager is not initialized. Call create_chat_manager() first.")

        self.logger.info("Executing single prompt...")
        responses = self.chat_manager.execute_prompts_single_chat([prompt_text], cycle_speed=2)
        self.logger.info("Prompt execution completed. Received %d responses.", len(responses))
        return responses

    def start_prompt_cycle(self, selected_prompt_names: list) -> None:
        """
        Execute a prompt cycle across all available chats.
        
        :param selected_prompt_names: List of prompt names to execute.
        """
        if not self.chat_manager:
            raise RuntimeError("ChatManager is not initialized. Call create_chat_manager() first.")

        all_chats = self.chat_manager.get_all_chat_titles()
        if not all_chats:
            self.logger.info("No chats found. Aborting prompt cycle.")
            return

        filtered_chats = [chat for chat in all_chats if chat.get("title") not in self.config.excluded_chats]
        self.logger.info("Starting prompt cycle for %d chats.", len(filtered_chats))

        for chat in filtered_chats:
            chat_title = chat.get("title", "Unknown Chat")
            chat_link = chat.get("link")
            self.logger.info("Processing chat: %s", chat_title)

            if not chat_link:
                self.logger.warning("Skipping chat '%s' due to missing link.", chat_title)
                continue

            # Navigate to the chat and allow time for it to load
            driver = self.chat_manager.driver_manager.get_driver()
            driver.get(chat_link)
            time.sleep(3)

            chat_responses = []
            for prompt_name in selected_prompt_names:
                # Load prompt text from prompt manager
                prompt_text = self.prompt_manager.get_prompt(prompt_name)
                if not prompt_text:
                    self.logger.warning("Empty prompt for '%s'; skipping.", prompt_name)
                    continue

                self.logger.info("Sending prompt '%s' to chat '%s'", prompt_name, chat_title)
                if not self.chat_manager.prompt_engine.send_prompt(prompt_text):
                    self.logger.error("Failed to send prompt '%s' in chat '%s'", prompt_name, chat_title)
                    continue

                response = self.chat_manager.prompt_engine.wait_for_stable_response()
                if not response:
                    self.logger.warning("No stable response for prompt '%s' in chat '%s'", prompt_name, chat_title)
                    continue

                # Special handling for 'dreamscape' prompt: auto-episode management
                if prompt_name.lower() == "dreamscape":
                    episode_counter = self.prompt_manager.prompts.get("dreamscape", {}).get("episode_counter", 1)
                    chat_filename = f"episode_{episode_counter}_{sanitize_filename(chat_title)}.txt"
                    self.prompt_manager.prompts["dreamscape"]["episode_counter"] = episode_counter + 1
                    self.prompt_manager.save_prompts()
                    if self.discord:
                        self.discord.send_message(
                            f"New Dreamscape Episode from '{chat_title}':\n{response}"
                        )
                        self.logger.info("Posted new Dreamscape episode to Discord for '%s'", chat_title)
                else:
                    chat_filename = f"{sanitize_filename(chat_title)}.txt"

                # Save the response to a file
                prompt_dir = os.path.join("responses", sanitize_filename(chat_title), sanitize_filename(prompt_name))
                os.makedirs(prompt_dir, exist_ok=True)
                chat_file_path = os.path.join(prompt_dir, chat_filename)
                try:
                    with open(chat_file_path, 'w', encoding='utf-8') as f:
                        f.write(response)
                    self.logger.info("Saved response for chat '%s' to %s", chat_title, chat_file_path)
                except Exception as e:
                    self.logger.error("Error saving response for chat '%s': %s", chat_title, e)

                chat_responses.append({
                    "prompt_name": prompt_name,
                    "prompt_text": prompt_text,
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                    "ai_observations": self.analyze_execution_response(response, prompt_text)
                })
                time.sleep(1)

            run_metadata = {
                "timestamp": datetime.now().isoformat(),
                "model": self.chat_manager.model,
                "chat_count": 1,
                "execution_time": f"{round(time.time(), 2)}s",
                "bottlenecks": []
            }
            output_dir = os.path.join("responses", sanitize_filename(chat_title))
            generate_full_run_json(chat_title, chat_link, chat_responses, run_metadata, output_dir)
            self.logger.info("Saved full_run.json for chat '%s'.", chat_title)

        self.logger.info("Completed full prompt cycle across all chats.")

    # --- Prompt Management ---

    def load_prompt(self, prompt_type: str) -> (str, str):
        """
        Load a prompt and its associated model.
        
        :param prompt_type: The name of the prompt.
        :return: Tuple of (prompt_text, model).
        """
        try:
            prompt_text = self.prompt_manager.get_prompt(prompt_type)
            model = self.prompt_manager.get_model(prompt_type)
            self.logger.info("Loaded prompt '%s' with model '%s'.", prompt_type, model)
            return prompt_text, model
        except Exception as e:
            self.logger.error("Error loading prompt '%s': %s", prompt_type, e)
            raise RuntimeError(e)

    def save_prompt(self, prompt_type: str, prompt_text: str) -> None:
        """
        Save or update a prompt.
        
        :param prompt_type: The prompt identifier.
        :param prompt_text: The prompt content.
        """
        self.prompt_manager.save_prompt(prompt_type, prompt_text)
        self.logger.info("Prompt '%s' saved.", prompt_type)

    def reset_prompts(self) -> None:
        """
        Reset all prompts to their default values.
        """
        self.prompt_manager.reset_to_defaults()
        self.logger.info("Prompts have been reset to defaults.")

    # --- Discord Bot Management ---

    def launch_discord_bot(self, bot_token: str, channel_id: int, log_callback=None) -> None:
        """
        Launch the Discord bot if it's not already running.
        All Discord lifecycle management is handled here.
        
        :param bot_token: Discord bot token.
        :param channel_id: Default channel ID.
        :param log_callback: Optional callback for logging Discord messages.
        """
        if self.discord and self.discord.is_running:
            self.logger.warning("Discord bot is already running.")
            return

        # Initialize UnifiedDiscordService with configuration
        self.discord = UnifiedDiscordService(
            bot_token=bot_token,
            default_channel_id=channel_id,
            template_dir=os.path.join(self.config.template_dir, "discord")
        )
        
        # Set up logging callback
        if log_callback:
            self.discord.set_log_callback(log_callback)
        else:
            self.discord.set_log_callback(lambda msg: self.logger.info("Discord: %s", msg))

        # Start the bot
        self.discord.run()
        self.logger.info("Discord bot launched.")

    def stop_discord_bot(self) -> None:
        """
        Stop the Discord bot if it is running.
        This method ensures that the Discord lifecycle is managed only by DreamscapeService.
        """
        if self.discord and self.discord.is_running:
            self.discord.stop()
            self.logger.info("Discord bot stopped.")
        else:
            self.logger.warning("Discord bot is not running.")

    def send_discord_message(self, message: str, channel_id: int = None) -> None:
        """
        Send a message through Discord.
        
        :param message: The message to send.
        :param channel_id: Optional channel ID (uses default if not specified).
        """
        if not self.discord or not self.discord.is_running:
            self.logger.warning("Discord bot is not running.")
            return

        self.discord.send_message(message, channel_id)

    def send_discord_file(self, file_path: str, content: str = "", channel_id: int = None) -> None:
        """
        Send a file through Discord.
        
        :param file_path: Path to the file to send.
        :param content: Optional message to send with the file.
        :param channel_id: Optional channel ID (uses default if not specified).
        """
        if not self.discord or not self.discord.is_running:
            self.logger.warning("Discord bot is not running.")
            return

        self.discord.send_file(file_path, content, channel_id)

    def send_discord_template(self, template_name: str, context: dict, channel_id: int = None) -> None:
        """
        Send a templated message through Discord.
        
        :param template_name: Name of the template to use.
        :param context: Dictionary of context variables for the template.
        :param channel_id: Optional channel ID (uses default if not specified).
        """
        if not self.discord or not self.discord.is_running:
            self.logger.warning("Discord bot is not running.")
            return

        self.discord.send_template(template_name, context, channel_id)

    def get_discord_status(self) -> dict:
        """Get current Discord bot status."""
        if not self.discord:
            return {
                "is_running": False,
                "message": "Discord bot not initialized"
            }
        return self.discord.get_status()

    # --- Reinforcement Tools ---

    async def run_prompt_tuning(self) -> None:
        """
        Execute prompt tuning using the reinforcement engine.
        """
        self.reinforcement_engine.auto_tune_prompts(self.prompt_manager)
        self.logger.info("Prompt tuning completed. Memory updated on %s", 
                         self.reinforcement_engine.memory_data.get('last_updated'))

    # --- Dreamscape Generation ---
    
    async def generate_dreamscape_content(self, headless: bool = None, excluded_chats: list = None) -> list:
        """
        Generate Dreamscape content by running the original Digital Dreamscape workflow.
        This method visits each ChatGPT chat and generates a creative narrative episode.
        
        Args:
            headless: Whether to run the browser in headless mode
            excluded_chats: List of chat titles to exclude
            
        Returns:
            List of generated dreamscape entries
        """
        # Ensure chat manager is initialized
        if not self.chat_manager:
            self.logger.info("Chat manager not initialized. Creating a new instance.")
            self.create_chat_manager(headless=headless, excluded_chats=excluded_chats)
            
        # Ensure the chat manager is ready
        if not self.chat_manager:
            raise RuntimeError("Failed to initialize ChatManager for Dreamscape generation")
            
        # Get the output directory from config or use default
        output_dir = self.config.get("dreamscape_output_dir", "outputs/dreamscape") if hasattr(self.config, "get") else getattr(self.config, "dreamscape_output_dir", "outputs/dreamscape")
        
        # Initialize the generator if needed
        if not hasattr(self.dreamscape_generator, 'generate_dreamscape_episodes'):
            self.logger.warning("Dreamscape generator doesn't support the original functionality. Re-initializing.")
            self.dreamscape_generator = DreamscapeGenerationService(
                chat_manager=self.chat_manager,
                response_handler=self.prompt_handler,
                output_dir=output_dir,
                discord_manager=self.discord
            )
            
        # Run the generation process
        self.logger.info("Starting Dreamscape content generation process...")
        try:
            entries = await self.dreamscape_generator.generate_dreamscape_episodes()
            self.logger.info(f"Dreamscape generation completed successfully with {len(entries) if entries else 0} entries.")
            return entries
        except Exception as e:
            self.logger.error(f"Error during Dreamscape generation: {str(e)}")
            raise
            
    def get_dreamscape_context(self) -> dict:
        """
        Get the current Dreamscape context memory.
        
        Returns:
            Dictionary with context information including themes, episode count, etc.
        """
        if not hasattr(self.dreamscape_generator, 'get_context_summary'):
            self.logger.warning("Dreamscape generator doesn't support context summary. Returning empty data.")
            return {
                "episode_count": 0,
                "last_updated": None,
                "active_themes": [],
                "recent_episodes": []
            }
            
        try:
            return self.dreamscape_generator.get_context_summary()
        except Exception as e:
            self.logger.error(f"Error retrieving Dreamscape context: {str(e)}")
            return {
                "episode_count": 0,
                "last_updated": None,
                "active_themes": [],
                "recent_episodes": [],
                "error": str(e)
            }
            
    def send_context_to_chatgpt(self, chat_name: str = None) -> bool:
        """
        Automatically send the current Dreamscape context to ChatGPT.
        This ensures ChatGPT has the latest narrative context for future episode generation.
        
        Args:
            chat_name: Optional specific chat to send context to. If None, uses "Dreamscape" or first available.
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Ensure chat manager exists
        if not self.chat_manager:
            try:
                self.create_chat_manager()
            except Exception as e:
                self.logger.error(f"Failed to create chat manager for context update: {str(e)}")
                return False
                
        if not self.chat_manager:
            self.logger.error("Cannot send context to ChatGPT: Chat manager not available")
            return False
            
        try:
            # Get the formatted context prompt
            if not hasattr(self.dreamscape_generator, 'get_chatgpt_context_prompt'):
                self.logger.error("Dreamscape generator doesn't support context prompt generation")
                return False
                
            context_prompt = self.dreamscape_generator.get_chatgpt_context_prompt()
            if not context_prompt:
                self.logger.warning("Empty context prompt generated, nothing to send")
                return False
                
            # Get all available chats
            all_chats = self.chat_manager.get_all_chat_titles()
            if not all_chats:
                self.logger.error("No chats available to send context to")
                return False
                
            # Find the target chat - either by name or first available
            target_chat = None
            if chat_name:
                # Try to find the specified chat
                for chat in all_chats:
                    if chat.get('title', '').lower() == chat_name.lower():
                        target_chat = chat
                        break
            else:
                # Look for a "Dreamscape" chat first
                for chat in all_chats:
                    if "dreamscape" in chat.get('title', '').lower():
                        target_chat = chat
                        break
                        
                # If no Dreamscape chat, use the first chat that's not excluded
                if not target_chat:
                    excluded = self.config.get("excluded_chats", []) if hasattr(self.config, "get") else getattr(self.config, "excluded_chats", [])
                    for chat in all_chats:
                        title = chat.get('title', '')
                        if title and title not in excluded:
                            target_chat = chat
                            break
                            
            if not target_chat:
                self.logger.error("No suitable chat found to send context to")
                return False
                
            # Navigate to the chat
            chat_url = target_chat.get('link')
            if not chat_url:
                self.logger.error(f"No link available for chat: {target_chat.get('title')}")
                return False
                
            # Add model parameter if needed
            if "model=gpt-4o" not in chat_url:
                chat_url += ("&" if "?" in chat_url else "?") + "model=gpt-4o"
                
            # Get the driver and navigate to the chat
            driver = self.chat_manager.driver_manager.get_driver()
            driver.get(chat_url)
            time.sleep(5)  # Wait for page to load
            
            # Send the context prompt
            self.logger.info(f"Sending context update to chat: {target_chat.get('title')}")
            result = self.chat_manager.prompt_engine.send_prompt(context_prompt)
            
            # Wait for response if needed
            if result:
                response = self.chat_manager.prompt_engine.wait_for_stable_response()
                self.logger.info("Context update acknowledged by ChatGPT")
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error sending context to ChatGPT: {str(e)}")
            return False
            
    def schedule_context_updates(self, interval_days: int = 7, chat_name: str = None) -> bool:
        """
        Schedule regular context updates to be sent to ChatGPT.
        
        Args:
            interval_days: How often to send updates (in days)
            chat_name: Specific chat to target for updates
            
        Returns:
            bool: True if scheduled successfully
        """
        # This would be implemented with a scheduler like APScheduler
        # For now, we'll simulate by creating a timestamp file
        
        try:
            schedule_file = os.path.join(self.config.get("dreamscape_output_dir", "outputs/dreamscape"), 
                                        "context_update_schedule.json")
            
            schedule_data = {
                "enabled": True,
                "interval_days": interval_days,
                "target_chat": chat_name,
                "last_update": datetime.now().isoformat(),
                "next_update": (datetime.now() + timedelta(days=interval_days)).isoformat()
            }
            
            with open(schedule_file, "w", encoding="utf-8") as f:
                json.dump(schedule_data, f, indent=2)
                
            self.logger.info(f"Scheduled context updates every {interval_days} days")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to schedule context updates: {str(e)}")
            return False
    
    # --- Execution Response Analysis ---

    def analyze_execution_response(self, response: str, prompt_text: str) -> dict:
        """
        Analyze an AI execution response to extract performance metrics.
        
        :param response: The AI response text.
        :param prompt_text: The prompt text that was executed.
        :return: A dictionary of analysis results.
        """
        analysis = self.chat_manager.analyze_execution_response(response, prompt_text)
        self.logger.info("Response analysis completed.")
        return analysis

    @property
    def discord(self):
        """
        Returns the Discord manager service if available.
        
        Returns:
            DiscordManager or None: The Discord manager service or None if not initialized.
        """
        return self.get_service("discord_manager")
        
    @discord.setter
    def discord(self, manager):
        """
        Sets the Discord manager service.
        
        Args:
            manager: The Discord manager instance to set.
        """
        self.set_service("discord_manager", manager)

    def bootstrap_services(self):
        """
        Bootstrap all services with correct initialization order and proper dependency management.
        This ensures services are available before they're needed by other services.
        
        Returns:
            bool: True if all critical services were initialized successfully
        """
        self.logger.info("Bootstrapping services in correct dependency order...")
        
        # Initialize service registry if it doesn't exist
        if not hasattr(self, "_services"):
            self._services = {}
            
        # Step 1: Initialize core independent services first
        from core.UnifiedDiscordService import UnifiedDiscordService
        from core.AletheiaPromptManager import AletheiaPromptManager
        from core.ChatManager import ChatManager
        
        try:
            # Create Discord manager
            bot_token = self.config.get("discord_token", "") if hasattr(self.config, "get") else getattr(self.config, "discord_token", "")
            channel_id = self.config.get("discord_channel_id", "") if hasattr(self.config, "get") else getattr(self.config, "discord_channel_id", "")
            
            # Get template directory from config or use default
            template_dir = self.config.get("discord_template_dir", "") if hasattr(self.config, "get") else getattr(self.config, "discord_template_dir", "")
            if not template_dir:
                template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates", "discord_templates")
                
            # Initialize Discord service with proper error handling
            discord_manager = UnifiedDiscordService(
                bot_token=bot_token, 
                default_channel_id=channel_id,
                template_dir=template_dir
            )
            self.set_service("discord_manager", discord_manager)
            self.logger.info("Discord manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Discord manager: {str(e)}")
            self.set_service("discord_manager", self._create_empty_service("discord_manager"))
            
        try:
            # Create prompt manager
            memory_file = self.config.get("memory_file", "memory/dreamscape_memory.json") if hasattr(self.config, "get") else getattr(self.config, "memory_file", "memory/dreamscape_memory.json")
            prompt_manager = AletheiaPromptManager(memory_file=memory_file)
            self.set_service("prompt_manager", prompt_manager)
            self.logger.info("Prompt manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize prompt manager: {str(e)}")
            self.set_service("prompt_manager", self._create_empty_service("prompt_manager"))
            
        try:
            # Create chat manager
            model = self.config.get("default_model", "gpt-4") if hasattr(self.config, "get") else getattr(self.config, "default_model", "gpt-4")
            headless = self.config.get("headless", True) if hasattr(self.config, "get") else getattr(self.config, "headless", True)
            excluded_chats = self.config.get("excluded_chats", []) if hasattr(self.config, "get") else getattr(self.config, "excluded_chats", [])
            
            chat_manager = ChatManager(
                config=self.config,
                logger=self.logger
            )
            self.set_service("chat_manager", chat_manager)
            self.logger.info("Chat manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize chat manager: {str(e)}")
            self.set_service("chat_manager", self._create_empty_service("chat_manager"))
            
        # Step 2: Initialize dependent services
        try:
            # Create reinforcement engine
            from core.ReinforcementEngine import ReinforcementEngine
            reinforcement_engine = ReinforcementEngine(
                config_manager=self.config,
                logger=self.logger
            )
            self.set_service("reinforcement_engine", reinforcement_engine)
            self.logger.info("Reinforcement engine initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize reinforcement engine: {str(e)}")
            self.set_service("reinforcement_engine", self._create_empty_service("reinforcement_engine"))
            
        try:
            # Create prompt handler
            from core.PromptResponseHandler import PromptResponseHandler
            prompt_handler = PromptResponseHandler(
                config_manager=self.config,
                logger=self.logger
            )
            self.set_service("prompt_handler", prompt_handler)
            self.logger.info("Prompt handler initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize prompt handler: {str(e)}")
            self.set_service("prompt_handler", self._create_empty_service("prompt_handler"))
            
        # Ensure critical services are registered for property access
        if self.get_service("discord_manager") and not hasattr(self, "_services"):
            self._services = {}
            self._services["discord_manager"] = self.get_service("discord_manager")
            
        # Step 3: Initialize other services that depend on the core services
        # Add more service initializations here as needed
            
        # Return success status based on critical services
        critical_services = ["discord_manager", "prompt_manager", "chat_manager"]
        all_critical_available = all(
            self.get_service(svc) is not None and 
            not (hasattr(self.get_service(svc), "is_empty_service") and 
                self.get_service(svc).is_empty_service())
            for svc in critical_services
        )
        
        service_status = ", ".join([
            f"{svc}: {'✓' if self.get_service(svc) is not None and not (hasattr(self.get_service(svc), 'is_empty_service') and self.get_service(svc).is_empty_service()) else '✗'}"
            for svc in critical_services
        ])
        
        self.logger.info(f"Service bootstrap complete. Status: {service_status}")
        return all_critical_available

    def shutdown_all(self):
        """
        Gracefully shuts down all services.
        Called when the application is closing.
        """
        self.logger.info("Shutting down all services...")
        
        # List of service methods to call on shutdown
        shutdown_methods = {
            "chat_manager": "shutdown",
            "discord_manager": "shutdown",
            "prompt_manager": "save_state",
            "memory_manager": "save",
        }
        
        for service_name, method_name in shutdown_methods.items():
            service = getattr(self, service_name, None)
            if service is not None and hasattr(service, method_name):
                try:
                    self.logger.info(f"Shutting down {service_name}...")
                    method = getattr(service, method_name)
                    method()
                except Exception as e:
                    self.logger.error(f"Error shutting down {service_name}: {e}")
            else:
                self.logger.debug(f"Service {service_name} not available or doesn't have method {method_name}")
        
        self.logger.info("All services shut down successfully")

    def _initialize_dreamscape_generator(self) -> Optional[DreamscapeGenerationService]:
        """Initialize the Dreamscape Episode Generator service."""
        if not self.chat_manager or not self.prompt_handler or not self.config:
            self.logger.warning(
                "Cannot initialize DreamscapeGenerator: Missing ChatManager, PromptHandler, or Config."
            )
            return None
        try:
            output_dir = self.path_manager.get_path("dreamscape_episodes", "episodes")
            # Make sure to instantiate DreamscapeGenerationService here
            dreamscape_generator = DreamscapeGenerationService(
                chat_manager=self.chat_manager,
                response_handler=self.prompt_handler, # Note: Engine expects response_handler, adjust if needed
                # Assuming engine can get path_manager or output_dir needs to be passed
                # Assuming TemplateManager is injected or accessible
                # Assuming discord_manager is optional or passed if needed
            )
            self.logger.info("✅ Dreamscape Generation Service Initialized")
            return dreamscape_generator
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize DreamscapeGenerator: {e}", exc_info=True)
            return None
