#!/usr/bin/env python3
"""
Service Registry - Standard Service Interfaces and Factory Methods
=================================================================

This module defines standard interfaces for all services and provides
factory methods to create and register them with the service container.

Design rationale:
- Standardized service interfaces ensure consistent behavior.
- Factory methods handle dependency resolution automatically and use
  lazy imports to reduce startup overhead.
- Centralized registry simplifies service management.
- Each service can be individually tested or mocked.
"""

import logging
import os
import json
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Protocol

# Core interfaces and factories
from core.interfaces.IPromptManager import IPromptManager
from core.interfaces.IPromptOrchestrator import IPromptOrchestrator
from core.interfaces.IDreamscapeService import IDreamscapeService
from core.micro_factories.prompt_factory import PromptFactory
from core.micro_factories.orchestrator_factory import OrchestratorFactory

# Note: DreamscapeFactory is imported dynamically when needed to avoid circular imports

# -----------------------------------------------------------------------------
# Service Interface Protocols
# -----------------------------------------------------------------------------

class LoggingService(Protocol):
    def info(self, msg: str, *args, **kwargs) -> None: ...
    def warning(self, msg: str, *args, **kwargs) -> None: ...
    def error(self, msg: str, *args, **kwargs) -> None: ...
    def debug(self, msg: str, *args, **kwargs) -> None: ...


class ConfigService(Protocol):
    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
    def load(self, config_file: str) -> None: ...
    def save(self, config_file: Optional[str] = None) -> None: ...


class UnifiedPromptService(Protocol):
    def get_prompt(self, prompt_type: str) -> str: ...
    def save_prompt(self, prompt_type: str, prompt_text: str) -> None: ...
    def get_model(self, prompt_type: str) -> str: ...
    def reset_to_defaults(self) -> None: ...


class MemoryService(Protocol):
    def load(self) -> Dict[str, Any]: ...
    def save(self, data: Dict[str, Any]) -> None: ...
    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
    def clear(self) -> None: ...


class ChatService(Protocol):
    def execute_prompts_single_chat(self, prompts: List[str], cycle_speed: int = 1) -> List[str]: ...
    def get_all_chat_titles(self) -> List[Dict[str, str]]: ...
    def shutdown_driver(self) -> None: ...


class DiscordService(Protocol):
    def run(self) -> None: ...
    def stop(self) -> None: ...
    def send_message(self, message: str, channel_id: Optional[int] = None) -> None: ...
    def send_file(self, file_path: str, content: str = "", channel_id: Optional[int] = None) -> None: ...
    def send_template(self, template_name: str, context: Dict[str, Any], channel_id: Optional[int] = None) -> None: ...
    def get_status(self) -> Dict[str, Any]: ...


class ReinforcementService(Protocol):
    def auto_tune_prompts(self, prompt_manager: Any) -> None: ...
    def apply_fix(self, code: str, error_message: str) -> str: ...
    def rollback_changes(self, snapshot_id: str) -> str: ...


class CursorService(Protocol):
    def execute_prompt(self, prompt: str, context: Dict[str, Any] = None) -> str: ...
    def debug_code(self, code: str, error: str = None) -> Dict[str, Any]: ...
    def shutdown_all(self) -> None: ...


# -----------------------------------------------------------------------------
# Factory Functions with Lazy Imports and Robust Handling
# -----------------------------------------------------------------------------

def create_config_service(config_name: str = "dreamscape_config.yaml") -> Any:
    from config.ConfigManager import ConfigManager  # Lazy import
    try:
        config = ConfigManager(config_name=config_name)
        logging.info(f"Configuration loaded from {config_name}")
        return config
    except Exception as e:
        logging.error(f"Failed to load configuration from {config_name}: {str(e)}")
        # Return a stub implementation
        return type('ConfigStub', (), {
            'get': lambda self, key, default=None: default,
            'set': lambda self, key, value: None,
            'load': lambda self, file: None,
            'save': lambda self, file=None: None
        })()


def create_logging_service() -> Any:
    logger = logging.getLogger()
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
    """Create and configure the UnifiedPromptService with all required dependencies."""
    from core.services.prompt_execution_service import UnifiedPromptService
    from core.PathManager import PathManager
    from core.DriverManager import DriverManager
    from config.ConfigManager import ConfigManager
    
    if not config_service:
        logging.error("Cannot create prompt service without configuration")
        return _create_empty_service("prompt_service")
    
    try:
        # Create required dependencies
        config_manager = ConfigManager()
        path_manager = PathManager()
        driver_manager = DriverManager(config_service)
        
        # Get prompt manager using the factory
        prompt_manager = get_service("prompt_manager")
        if not prompt_manager:
            prompt_manager = PromptFactory.create_prompt_manager()
        
        # Get feedback engine from registry or create new
        feedback_engine = get_service("feedback_engine")
        
        # Create UnifiedPromptService with all dependencies
        prompt_service = UnifiedPromptService(
            config_manager=config_manager,
            path_manager=path_manager,
            config_service=config_service,
            prompt_manager=prompt_manager,
            driver_manager=driver_manager,
            feedback_engine=feedback_engine,
            model=config_service.get("default_model", "gpt-4o-mini")
        )
        
        logging.info("UnifiedPromptService initialized successfully")
        return prompt_service
        
    except Exception as e:
        logging.error(f"Failed to initialize UnifiedPromptService: {str(e)}")
        return _create_empty_service("prompt_service")


def create_chat_service(config_service: Any = None) -> Any:
    """Create and configure the chat service."""
    from core.ChatManager import ChatManager  # Lazy import
    from config.ConfigManager import ConfigManager  # For type-checking
    import json
    if not config_service:
        logging.error("Cannot create chat service without configuration")
        return _create_empty_service("chat_service")
    try:
        model = config_service.get("default_model", "gpt-4")
        headless = config_service.get("headless", True)
        excluded_chats = config_service.get("excluded_chats", [])
        memory_path = config_service.get("memory_path", "memory/chat_memory.json")
        # Handle case where memory_path is a ConfigManager
        if isinstance(memory_path, ConfigManager):
            memory_path = memory_path.get("memory_path", "memory/chat_memory.json")
        if hasattr(memory_path, 'get_path'):
            memory_path = memory_path.get_path()
        elif not isinstance(memory_path, (str, os.PathLike)):
            memory_path = str(memory_path)
        os.makedirs(os.path.dirname(memory_path), exist_ok=True)
        # Initialize empty memory file if needed
        if not os.path.exists(memory_path) or os.path.getsize(memory_path) == 0:
            default_memory = {
                "chats": [],
                "last_update": datetime.now().isoformat(),
                "settings": {
                    "model": model,
                    "headless": headless
                }
            }
            with open(memory_path, 'w', encoding='utf-8') as f:
                json.dump(default_memory, f, indent=2)
            logging.info(f"Initialized new chat memory file at {memory_path}")
        
        driver_options = {
            "headless": headless,
            "window_size": (1920, 1080),
            "disable_gpu": True,
            "no_sandbox": True,
            "disable_dev_shm": True
        }
        
        chat_manager = ChatManager(
            driver_options=driver_options,
            excluded_chats=excluded_chats,
            model=model,
            timeout=180,
            stable_period=10,
            poll_interval=5,
            headless=headless,
            memory_file=memory_path
        )
        
        logging.info(f"ChatManager initialized with memory path: {memory_path}")
        return chat_manager
        
    except Exception as e:
        logging.error(f"Failed to initialize chat service: {str(e)}")
        return _create_empty_service("chat_service")


def create_discord_service(config_service: Any = None, logger_obj: Any = None) -> Any:
    from core.UnifiedDiscordService import UnifiedDiscordService  # Lazy import
    import inspect
    try:
        discord_params = inspect.signature(UnifiedDiscordService.__init__).parameters
        if 'config' in discord_params and config_service and 'logger' in discord_params and logger_obj:
            return UnifiedDiscordService(config=config_service, logger=logger_obj)
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
        return UnifiedDiscordService()
    except Exception as e:
        logging.error(f"Failed to initialize Discord service: {str(e)}")
        return _create_empty_service("discord_service")


def create_cursor_service(config_service: Any = None, memory_service: Any = None) -> Any:
    try:
        from core.refactor.CursorSessionManager import CursorSessionManager  # Lazy import
        if not config_service or not memory_service:
            logging.error("Cannot create cursor service without config and memory services")
            return _create_empty_service("cursor_service")
        return CursorSessionManager(config_service, memory_service)
    except Exception as e:
        logging.error(f"Failed to initialize cursor service: {str(e)}")
        return _create_empty_service("cursor_service")


def create_reinforcement_service(config_service: Any = None, logger_obj: Any = None) -> Any:
    from core.ReinforcementEngine import ReinforcementEngine  # Lazy import
    try:
        return ReinforcementEngine(config_service, logger_obj or logging.getLogger())
    except Exception as e:
        logging.error(f"Failed to initialize reinforcement service: {str(e)}")
        return _create_empty_service("reinforcement_service")


def create_cycle_service(config_service: Any = None, prompt_service: Any = None,
                         chat_service: Any = None, response_handler: Any = None,
                         memory_service: Any = None, discord_service: Any = None) -> Any:
    from core.CycleExecutionService import CycleExecutionService  # Lazy import
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
        return _create_empty_service("cycle_service")


def create_response_handler(config_service: Any = None) -> Any:
    from core.PromptResponseHandler import PromptResponseHandler  # Lazy import
    try:
        return PromptResponseHandler(
            config_service,
            logging.getLogger("ResponseHandler")
        )
    except Exception as e:
        logging.error(f"Failed to initialize response handler: {str(e)}")
        return _create_empty_service("response_handler")


def create_task_orchestrator() -> Any:
    from core.TaskOrchestrator import TaskOrchestrator  # Lazy import
    try:
        return TaskOrchestrator(logging.getLogger("TaskOrchestrator"))
    except Exception as e:
        logging.error(f"Failed to initialize task orchestrator: {str(e)}")
        return _create_empty_service("task_orchestrator")


def create_dreamscape_generator(*, config_service, chat_service, response_handler, discord_service=None) -> Any:
    """Create and configure the dreamscape generator service using the new factory."""
    factory = DreamscapeFactory(
        config_service=config_service,
        chat_service=chat_service,
        response_handler=response_handler,
        discord_service=discord_service,
        logger=logging.getLogger("DreamscapeGenerator")
    )
    return factory.create()


def create_memory_service(config_service: Any = None) -> Any:
    from core.MemoryManager import MemoryManager  # Lazy import
    try:
        memory_file = "memory/memory.json"
        if config_service:
            memory_file = config_service.get("memory_file", memory_file)
        if not isinstance(memory_file, (str, os.PathLike)):
            memory_file = str(memory_file)
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)
        # Auto-initialize memory file if it doesn't exist or is empty
        if not os.path.exists(memory_file) or os.path.getsize(memory_file) == 0:
            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            logging.info(f"Initialized new memory file at {memory_file}")
        return MemoryManager(memory_file=memory_file)
    except Exception as e:
        logging.error(f"Failed to initialize memory service: {str(e)}")
        return _create_empty_service("memory_service")


def create_template_manager(config_manager=None, logger=None):
    """Create and configure the template manager."""
    try:
        from core.TemplateManager import TemplateManager
        
        # Initialize with default data and logger
        default_data = {}
        if config_manager:
            default_data = config_manager.get('template_defaults', {})
        
        template_manager = TemplateManager(
            default_data=default_data,
            logger=logger
        )
        
        return template_manager
    except Exception as e:
        if logger:
            logger.error(f"Failed to create TemplateManager: {e}")
        return None


# -----------------------------------------------------------------------------
# Service Registry and Registration
# -----------------------------------------------------------------------------

class ServiceRegistry:
    """
    Central registry for managing and validating services.
    """
    _services: Dict[str, Any] = {}
    _config = None
    _logger = None
    
    def __init__(self):
        self._required_services = {
            "cycle_service": "Core service for managing execution cycles",
            "task_orchestrator": "Service for orchestrating and managing tasks",
            "dreamscape_generator": "Service for generating dreamscape episodes"
        }
        self.logger = logging.getLogger(__name__)

    @classmethod
    def register(cls, name: str, service: Any) -> None:
        cls._services[name] = service
        logging.info(f"Registered service: {name}")

    @classmethod
    def get(cls, name: str) -> Optional[Any]:
        if name not in cls._services:
            logging.warning(f"Service '{name}' not available - creating empty implementation")
            cls._services[name] = cls._create_empty_service(name)
        return cls._services[name]

    def validate_service_registry(self) -> List[str]:
        missing_services = []
        for service_name in self._required_services:
            if service_name not in self._services:
                self.logger.error(f"Required service '{service_name}' is missing")
                missing_services.append(service_name)
            elif self._is_empty_service(self._services[service_name]):
                self.logger.error(f"Service '{service_name}' is registered but is an empty implementation")
                missing_services.append(service_name)
        return missing_services

    def _is_empty_service(self, service: Any) -> bool:
        return hasattr(service, '_is_empty_implementation') and service._is_empty_implementation

    @classmethod
    def _create_empty_service(cls, name: str) -> Any:
        class EmptyService:
            def __init__(self):
                self._is_empty_implementation = True
                self.logger = logging.getLogger(f"EmptyService.{name}")

            def __getattr__(self, attr):
                self.logger.warning(f"Attempted to call '{attr}' on empty service implementation of '{name}'")
                return lambda *args, **kwargs: None

        return EmptyService()

    @classmethod
    def initialize(cls, config, logger):
        """Initialize the service registry with configuration."""
        cls._config = config
        cls._logger = logger
        cls._register_core_services()
    
    @classmethod
    def _register_core_services(cls):
        """Register all core services needed by the application."""
        try:
            # Register config manager if not already registered
            if "config_manager" not in cls._services and cls._config:
                cls.register_service("config_manager", cls._config)
            
            # Register logger if not already registered
            if "logger" not in cls._services and cls._logger:
                cls.register_service("logger", cls._logger)
                
            # Register prompt_manager using the factory
            if "prompt_manager" not in cls._services:
                try:
                    from core.factories.prompt_factory import PromptFactory
                    prompt_manager = PromptFactory.create(cls)
                    if prompt_manager:
                        cls.register_service("prompt_manager", prompt_manager)
                        cls._logger.info("PromptManager registered via factory")
                    else:
                        cls._logger.warning("PromptFactory returned None for prompt_manager")
                except Exception as e:
                    cls._logger.error(f"Failed to create PromptManager via factory: {e}")
            
            # Register chat manager using the factory
            if "chat_manager" not in cls._services:
                try:
                    from core.factories.chat_factory import ChatFactory
                    chat_manager = ChatFactory.create(cls)
                    cls.register_service("chat_manager", chat_manager)
                except Exception as e:
                    cls._logger.warning(f"Could not create ChatManager: {e}")
            
            # Import container here to avoid circular imports
            from core.service_container import container
            
            # Import DreamscapeFactory here to avoid circular imports
            from core.micro_factories.dreamscape_factory import DreamscapeFactory
            
            # Register Dreamscape service using the factory
            dreamscape_service = DreamscapeFactory(
                config_service=cls._config,
                chat_service=cls.get_service("chat_manager"),
                response_handler=cls.get_service("prompt_handler"),
                discord_service=cls.get_service("discord_manager"),
                logger=cls._logger
            ).create()
            cls.register_service("dreamscape_generation", dreamscape_service)
            
        except Exception as e:
            cls._logger.error(f"Error registering core services: {str(e)}")
    
    @classmethod
    def register_service(cls, name: str, service: object):
        """Register a service instance with the registry."""
        cls._services[name] = service
        cls._logger.info(f"Registered service: {name}")
    
    @classmethod
    def get_service(cls, name: str) -> object:
        """Get a service instance by name."""
        return cls._services.get(name)
    
    @classmethod
    def has_service(cls, name: str) -> bool:
        """Check if a service is registered."""
        return name in cls._services


def register_all_services() -> None:
    """
    Register all services with the service container in proper dependency order.
    """
    # Import container here to avoid circular imports
    from core.service_container import container
    
    container.register('logger', create_logging_service)
    container.register('config', create_config_service)
    container.register('prompt_manager', lambda: PromptFactory.create_prompt_manager())
    container.register('memory_manager', create_memory_service, ['config'])
    container.register('response_handler', create_response_handler, ['config'])
    container.register('chat_manager', create_chat_service, ['config'])
    container.register('discord_service', create_discord_service, ['config', 'logger'])
    container.register('discord_manager', lambda: container.get('discord_service'))
    container.register('reinforcement_engine', create_reinforcement_service, ['config', 'logger'])
    container.register('fix_service', lambda: container.get('reinforcement_engine'))
    container.register('rollback_service', lambda: container.get('reinforcement_engine'))
    container.register('cursor_manager', create_cursor_service, ['config', 'memory_manager'])
    container.register('cycle_service', create_cycle_service, 
                       ['config', 'prompt_manager', 'chat_manager', 'response_handler',
                        'memory_manager', 'discord_service'])
    container.register('task_orchestrator', create_task_orchestrator)
    container.register('dreamscape_generator', create_dreamscape_generator,
                       ['chat_manager', 'response_handler', 'discord_service', 'config'])
    container.register('memory_service', create_memory_service, ['config'])

# Helper functions to avoid circular imports
def get_service(name: str) -> Any:
    """Get a service from the registry."""
    try:
        # Import container here to avoid circular imports
        from core.service_container import container
        return container.get(name)
    except Exception as e:
        logging.error(f"Error getting service {name}: {e}")
        return _create_empty_service(name)

def _create_empty_service(name: str) -> Any:
    """Create an empty service implementation."""
    class EmptyService:
        def __init__(self):
            self._is_empty_implementation = True
            self.logger = logging.getLogger(f"EmptyService.{name}")

        def __getattr__(self, attr):
            self.logger.warning(f"Attempted to call '{attr}' on empty service implementation of '{name}'")
            return lambda *args, **kwargs: None

    return EmptyService()

# -----------------------------------------------------------------------------
# End of Service Registry Module
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Example: register and validate all services.
    register_all_services()
    registry = ServiceRegistry()
    missing = registry.validate_service_registry()
    if missing:
        registry.logger.error(f"Missing required services: {missing}")
    else:
        registry.logger.info("All required services are registered and available.")
