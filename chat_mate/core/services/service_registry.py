#!/usr/bin/env python3
"""
Service Registry - Standard Service Interfaces and Factory Methods
=================================================================

This module defines standard interfaces for all services and provides
factory methods to create and register them with the service container.

Design rationale:
- Standardized service interfaces ensure consistent behavior
- Factory methods handle dependency resolution automatically
- Centralized registry simplifies service management
- Each service can be individually tested or mocked
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional, Protocol, Type, Union

from core.service_container import container


# Service Interface Protocols

class LoggingService(Protocol):
    """Interface for logging services."""
    def info(self, msg: str, *args, **kwargs) -> None: ...
    def warning(self, msg: str, *args, **kwargs) -> None: ...
    def error(self, msg: str, *args, **kwargs) -> None: ...
    def debug(self, msg: str, *args, **kwargs) -> None: ...


class ConfigService(Protocol):
    """Interface for configuration services."""
    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
    def load(self, config_file: str) -> None: ...
    def save(self, config_file: Optional[str] = None) -> None: ...


class PromptService(Protocol):
    """Interface for prompt management services."""
    def get_prompt(self, prompt_type: str) -> str: ...
    def save_prompt(self, prompt_type: str, prompt_text: str) -> None: ...
    def get_model(self, prompt_type: str) -> str: ...
    def reset_to_defaults(self) -> None: ...


class MemoryService(Protocol):
    """Interface for memory/persistence services."""
    def load(self) -> Dict[str, Any]: ...
    def save(self, data: Dict[str, Any]) -> None: ...
    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
    def clear(self) -> None: ...


class ChatService(Protocol):
    """Interface for chat interaction services."""
    def execute_prompts_single_chat(self, prompts: List[str], cycle_speed: int = 1) -> List[str]: ...
    def get_all_chat_titles(self) -> List[Dict[str, str]]: ...
    def shutdown_driver(self) -> None: ...


class DiscordService(Protocol):
    """Interface for Discord integration services."""
    def run(self) -> None: ...
    def stop(self) -> None: ...
    def send_message(self, message: str, channel_id: Optional[int] = None) -> None: ...
    def send_file(self, file_path: str, content: str = "", channel_id: Optional[int] = None) -> None: ...
    def send_template(self, template_name: str, context: Dict[str, Any], channel_id: Optional[int] = None) -> None: ...
    def get_status(self) -> Dict[str, Any]: ...


class ReinforcementService(Protocol):
    """Interface for reinforcement learning services."""
    def auto_tune_prompts(self, prompt_manager: Any) -> None: ...
    def apply_fix(self, code: str, error_message: str) -> str: ...
    def rollback_changes(self, snapshot_id: str) -> str: ...


class CursorService(Protocol):
    """Interface for Cursor integration services."""
    def execute_prompt(self, prompt: str, context: Dict[str, Any] = None) -> str: ...
    def debug_code(self, code: str, error: str = None) -> Dict[str, Any]: ...
    def shutdown_all(self) -> None: ...


# Service Factory Functions

def create_config_service(config_name: str = "dreamscape_config.yaml") -> Any:
    """Create and configure the configuration service."""
    from core.ConfigManager import ConfigManager
    
    try:
        config = ConfigManager(config_name=config_name)
        logging.info(f"Configuration loaded from {config_name}")
        return config
    except Exception as e:
        logging.error(f"Failed to load configuration from {config_name}: {str(e)}")
        # Create a stub that can at least handle basic operations
        return type('ConfigStub', (), {
            'get': lambda self, key, default=None: default,
            'set': lambda self, key, value: None,
            'load': lambda self, file: None,
            'save': lambda self, file=None: None
        })()


def create_logging_service() -> Any:
    """Create and configure the logging service."""
    logger = logging.getLogger()
    # Configure default logging if not already configured
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(os.path.join("outputs", "logs", "application.log"))
            ]
        )
    return logger


def create_prompt_service(config_service: Any = None) -> Any:
    """Create and configure the prompt service."""
    from core.AletheiaPromptManager import AletheiaPromptManager
    
    # Get memory file path from config or use default
    memory_file = "memory/dreamscape_memory.json"
    if config_service:
        memory_file = config_service.get("memory_file", memory_file)
    
    try:
        return AletheiaPromptManager(memory_file=memory_file)
    except Exception as e:
        logging.error(f"Failed to initialize prompt service: {str(e)}")
        return container._create_empty_service("prompt_service")


def create_chat_service(config_service: Any = None) -> Any:
    """Create and configure the chat service."""
    from core.ChatManager import ChatManager
    
    if not config_service:
        logging.error("Cannot create chat service without configuration")
        return container._create_empty_service("chat_service")
    
    try:
        model = config_service.get("default_model", "gpt-4")
        headless = config_service.get("headless", True)
        excluded_chats = config_service.get("excluded_chats", [])
        
        # Create driver options
        driver_options = {
            "headless": headless,
            "window_size": (1920, 1080),
            "disable_gpu": True,
            "no_sandbox": True,
            "disable_dev_shm": True
        }
        
        return ChatManager(
            driver_options=driver_options,
            excluded_chats=excluded_chats,
            model=model,
            timeout=180,
            stable_period=10,
            poll_interval=5,
            headless=headless
        )
    except Exception as e:
        logging.error(f"Failed to initialize chat service: {str(e)}")
        return container._create_empty_service("chat_service")


def create_discord_service(config_service: Any = None, logger: Any = None) -> Any:
    """Create and configure the Discord service."""
    from core.UnifiedDiscordService import UnifiedDiscordService
    import inspect
    
    try:
        # Check which parameters the constructor accepts
        discord_params = inspect.signature(UnifiedDiscordService.__init__).parameters
        
        # Different initialization based on the available constructor
        if 'config' in discord_params and config_service and 'logger' in discord_params and logger:
            return UnifiedDiscordService(config=config_service, logger=logger)
        
        # Fallback initialization with token and channel
        bot_token = ""
        channel_id = ""
        if config_service:
            bot_token = config_service.get("discord_token", "")
            channel_id = config_service.get("discord_channel_id", "")
        
        if 'bot_token' in discord_params and 'default_channel_id' in discord_params:
            template_dir = os.path.join("templates", "discord_templates")
            return UnifiedDiscordService(
                bot_token=bot_token,
                default_channel_id=channel_id,
                template_dir=template_dir
            )
        
        # Last resort: try the default constructor
        return UnifiedDiscordService()
    except Exception as e:
        logging.error(f"Failed to initialize Discord service: {str(e)}")
        return container._create_empty_service("discord_service")


def create_cursor_service(config_service: Any = None, memory_service: Any = None) -> Any:
    """Create and configure the Cursor service."""
    try:
        from core.CursorSessionManager import CursorSessionManager
        
        if not config_service or not memory_service:
            logging.error("Cannot create cursor service without config and memory services")
            return container._create_empty_service("cursor_service")
        
        cursor_url = config_service.get("cursor_url", "http://localhost:8000")
        return CursorSessionManager(config_service, memory_service)
    except Exception as e:
        logging.error(f"Failed to initialize cursor service: {str(e)}")
        return container._create_empty_service("cursor_service")


def create_reinforcement_service(config_service: Any = None, logger: Any = None) -> Any:
    """Create and configure the reinforcement service."""
    from core.ReinforcementEngine import ReinforcementEngine
    
    try:
        return ReinforcementEngine(config_service, logger or logging.getLogger())
    except Exception as e:
        logging.error(f"Failed to initialize reinforcement service: {str(e)}")
        return container._create_empty_service("reinforcement_service")


def create_cycle_service(config_service: Any = None, prompt_service: Any = None,
                        chat_service: Any = None, response_handler: Any = None,
                        memory_service: Any = None, discord_service: Any = None) -> Any:
    """Create and configure the cycle execution service."""
    from core.CycleExecutionService import CycleExecutionService
    
    try:
        return CycleExecutionService(
            config_manager=config_service,
            logger=logging.getLogger("CycleService"),
            prompt_manager=prompt_service,
            chat_manager=chat_service,
            response_handler=response_handler,
            memory_manager=memory_service,
            discord_manager=discord_service
        )
    except Exception as e:
        logging.error(f"Failed to initialize cycle service: {str(e)}")
        return container._create_empty_service("cycle_service")


def create_response_handler(config_service: Any = None) -> Any:
    """Create and configure the response handler service."""
    from core.PromptResponseHandler import PromptResponseHandler
    
    try:
        return PromptResponseHandler(
            config_service,
            logging.getLogger("ResponseHandler")
        )
    except Exception as e:
        logging.error(f"Failed to initialize response handler: {str(e)}")
        return container._create_empty_service("response_handler")


def create_task_orchestrator() -> Any:
    """Create and configure the task orchestrator service."""
    from core.TaskOrchestrator import TaskOrchestrator
    
    try:
        return TaskOrchestrator(logging.getLogger("TaskOrchestrator"))
    except Exception as e:
        logging.error(f"Failed to initialize task orchestrator: {str(e)}")
        return container._create_empty_service("task_orchestrator")


def create_dreamscape_generator(chat_service: Any = None, response_handler: Any = None,
                             discord_service: Any = None, config_service: Any = None) -> Any:
    """Create and configure the Dreamscape episode generator service."""
    from core.DreamscapeEpisodeGenerator import DreamscapeEpisodeGenerator
    
    try:
        output_dir = "outputs/dreamscape"
        if config_service:
            output_dir = config_service.get("dreamscape_output_dir", output_dir)
            
        return DreamscapeEpisodeGenerator(
            chat_manager=chat_service,
            response_handler=response_handler,
            output_dir=output_dir,
            discord_manager=discord_service
        )
    except Exception as e:
        logging.error(f"Failed to initialize Dreamscape generator: {str(e)}")
        return container._create_empty_service("dreamscape_generator")


# Function to register all services with the container
def register_all_services() -> None:
    """
    Register all services with the service container.
    This function handles proper dependency order.
    """
    # Register basic services first (no dependencies)
    container.register('logger', create_logging_service)
    container.register('config', create_config_service)
    
    # Register services with single dependencies
    container.register('prompt_manager', create_prompt_service, ['config'])
    
    # Use the prompt manager as memory manager too (dual role)
    container.register('memory_manager', lambda: container.get('prompt_manager'))
    
    # Register services with multiple dependencies
    container.register('response_handler', create_response_handler, ['config'])
    container.register('chat_manager', create_chat_service, ['config'])
    container.register('discord_service', create_discord_service, ['config', 'logger'])
    
    # Also register as 'discord_manager' for compatibility
    container.register('discord_manager', lambda: container.get('discord_service'))
    
    container.register('reinforcement_engine', create_reinforcement_service, ['config', 'logger'])
    
    # Register aliased services for compatibility
    container.register('fix_service', lambda: container.get('reinforcement_engine'))
    container.register('rollback_service', lambda: container.get('reinforcement_engine'))
    
    # Register complex services that depend on many other services
    container.register('cursor_manager', create_cursor_service, ['config', 'memory_manager'])
    container.register('cycle_service', create_cycle_service, 
                    ['config', 'prompt_manager', 'chat_manager', 'response_handler',
                    'memory_manager', 'discord_service'])
    container.register('task_orchestrator', create_task_orchestrator)
    container.register('dreamscape_generator', create_dreamscape_generator,
                    ['chat_manager', 'response_handler', 'discord_service', 'config']) 