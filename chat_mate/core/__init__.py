# AUTO-GENERATED __init__.py
# DO NOT EDIT MANUALLY - changes may be overwritten

from . import AIOutputLogAnalyzer
from . import AgentDispatcher
from . import AletheiaFeedbackLoopManager
from . import AletheiaPromptManager
from . import ChatManager
from . import ConfigManager
from . import ConsoleLogger
from . import CursorSessionManager
from . import CycleExecutionService
from . import DiscordBatchDispatcher
from . import DiscordLogger
from . import DiscordManager
from . import DiscordQueueProcessor
from . import DiscordTemplateManager
from . import DriverManager
# Legacy driver management - do not remove this line to maintain imports
# from . import DriverSessionManager
from . import EngagementAgent
from . import EventMessageBuilder
from . import FileLogger
from . import FileManager
from . import LoggerFactory
from . import MemoryManager
from . import NarrativeAnalytics
from . import OpenAIPromptEngine
from . import OptimizedMemoryManager
from . import PathManager
from . import PromptCycleOrchestrator
from . import PromptEngine
from . import PromptResponseHandler
from . import ReinforcementEngine
from . import ReinforcementEvaluator
from . import ReportExporter
from . import ResilientPromptExecutor
from . import ResponseHandler
from . import SystemHealthMonitor
from . import TaskManager
from . import TaskOrchestrator
from . import TemplateManager
from . import ThreadPoolManager
from . import UnifiedDiscordService
from . import UnifiedDreamscapeGenerator
from . import UnifiedDriverManager
from . import UnifiedFeedbackMemory
from . import UnifiedLoggingAgent
from . import UnifiedPromptEngine
from . import bootstrap
from . import chat_engine_simple
from . import config
from . import feedback
from . import reinforcement_tools

# Backward compatibility wrapper for DriverSessionManager
from .DriverManager import DriverManager as _DriverManager
class DriverSessionManager(_DriverManager):
    """
    Legacy wrapper for DriverSessionManager.
    This class is maintained for backward compatibility.
    It redirects all calls to the new unified DriverManager.
    """
    
    def __init__(self, config_manager=None, **kwargs):
        """Initialize with legacy DriverSessionManager signature."""
        # Extract configuration from config_manager if provided
        driver_options = {}
        if config_manager:
            # Map old config keys to new options
            driver_options = {
                'headless': config_manager.get('HEADLESS_MODE', False),
                'max_session_duration': config_manager.get('MAX_SESSION_DURATION', 3600),
                'retry_attempts': config_manager.get('DRIVER_RETRY_ATTEMPTS', 3),
                'retry_delay': config_manager.get('DRIVER_RETRY_DELAY', 5),
                'wait_timeout': config_manager.get('DRIVER_WAIT_TIMEOUT', 10),
                'undetected_mode': config_manager.get('USE_UNDETECTED_DRIVER', True),
            }
            
            # Add chrome options if provided in config
            chrome_options = config_manager.get('CHROME_OPTIONS', [])
            if chrome_options:
                driver_options['additional_arguments'] = chrome_options
        
        # Initialize with both config and any direct kwargs
        super().__init__(**{**driver_options, **kwargs})

__all__ = [
    'AIOutputLogAnalyzer',
    'AgentDispatcher',
    'AletheiaFeedbackLoopManager',
    'AletheiaPromptManager',
    'ChatManager',
    'ConfigManager',
    'ConsoleLogger',
    'CursorSessionManager',
    'CycleExecutionService',
    'DiscordBatchDispatcher',
    'DiscordLogger',
    'DiscordManager',
    'DiscordQueueProcessor',
    'DiscordTemplateManager',
    'DriverManager',
    'DriverSessionManager',
    'EngagementAgent',
    'EventMessageBuilder',
    'FileLogger',
    'FileManager',
    'LoggerFactory',
    'MemoryManager',
    'NarrativeAnalytics',
    'OpenAIPromptEngine',
    'OptimizedMemoryManager',
    'PathManager',
    'PromptCycleOrchestrator',
    'PromptEngine',
    'PromptResponseHandler',
    'ReinforcementEngine',
    'ReinforcementEvaluator',
    'ReportExporter',
    'ResilientPromptExecutor',
    'ResponseHandler',
    'SystemHealthMonitor',
    'TaskManager',
    'TaskOrchestrator',
    'TemplateManager',
    'ThreadPoolManager',
    'UnifiedDiscordService',
    'UnifiedDreamscapeGenerator',
    'UnifiedDriverManager',
    'UnifiedFeedbackMemory',
    'UnifiedLoggingAgent',
    'UnifiedPromptEngine',
    'bootstrap',
    'chat_engine_simple',
    'config',
    'feedback',
    'reinforcement_tools',
]
