"""
Default configuration values for the application.
This module contains the default configuration dictionary that defines
the base settings for all components of the system.
"""

from typing import Dict, Any
from pathlib import Path

def get_default_config() -> Dict[str, Any]:
    """
    Returns the default configuration dictionary.
    This is the base configuration that will be merged with user settings.
    """
    return {
        "version": "1.0.0",
        "app_name": "Dream.OS",
        "environment": "development",
        
        # Paths
        "paths": {
            "base": str(Path.cwd()),
            "config": "config",
            "logs": "logs",
            "outputs": "outputs",
            "memory": "memory",
            "templates": "templates",
            "drivers": "drivers",
            "cache": ".cache"
        },
        
        # Logging
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "application.log"
        },
        
        # ChatGPT Configuration
        "chat": {
            "default_model": "gpt-4",
            "headless": True,
            "timeout": 180,
            "stable_period": 10,
            "poll_interval": 5,
            "excluded_chats": [
                "ChatGPT",
                "Sora",
                "Explore GPTs",
                "Axiom",
                "work project",
                "prompt library",
                "Bot",
                "smartstock-pro"
            ]
        },
        
        # Discord Integration
        "discord": {
            "enabled": False,
            "token": "",
            "channel_id": "",
            "template_dir": "templates/discord"
        },
        
        # Memory Management
        "memory": {
            "chat_memory": "memory/chat_memory.json",
            "dreamscape_memory": "memory/dreamscape_memory.json",
            "system_memory": "memory/system_memory.json"
        },
        
        # Dreamscape Generation
        "dreamscape": {
            "output_dir": "outputs/dreamscape",
            "memory_file": "memory/dreamscape_memory.json",
            "default_prompt": (
                "You are the grand chronicler of the Digital Dreamscape—a mythic realm where "
                "Victor's life and work are reimagined as an evolving legend..."
            )
        },
        
        # WebDriver Configuration
        "webdriver": {
            "browser": "chrome",
            "headless": True,
            "window_size": (1920, 1080),
            "disable_gpu": True,
            "no_sandbox": True,
            "disable_dev_shm": True,
            "cache_dir": ".cache/selenium"
        },
        
        # System Settings
        "system": {
            "auto_login": False,
            "startup_validation": True,
            "memory_initialization": True
        }
    } 
