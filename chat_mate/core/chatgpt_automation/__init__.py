"""
ChatGPT Automation module for handling automated interactions with ChatGPT.
"""

# Avoid internal imports that cause circular dependencies.
# Consumers should import directly from the specific modules.

# Example: from core.chatgpt_automation.automation_engine import AutomationEngine

# Expose necessary setup functions if needed at package level
from .setup_logging import setup_logging

__all__ = [
    # 'ModelRegistry',  # Import from .model_registry
    # 'OpenAIClient', # Import from core.openai
    # 'PostProcessValidator', # Import from .post_process_validator
    # 'AutomationEngine', # Import from .automation_engine
    # 'BotWorker', # Import from .automation_engine
    # 'MultibotManager', # Import from .automation_engine
    # 'config', # Import from .config if needed
    # 'driver_factory', # Import from .driver_factory
    # 'local_llm_engine', # Import from .local_llm_engine
    # 'setup_chromedriver', # Import from .setup_chromedriver
    'setup_logging', # Keep setup_logging if needed at package level
    # Removed constants previously imported from config.py erroneously
    # 'BACKUP_FOLDER', 
    # 'DEPLOY_FOLDER',
    # 'LOG_FILE_PATH',
    # 'CONVERSATION_DIR',
]
