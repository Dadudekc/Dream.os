"""
Advanced Factory for creating DreamscapeGenerationService instances.

This is a stateful, standalone factory designed for use in CLI tools,
schedulers, and custom pipelines. It manages memory I/O, output directory
creation, and bootstraps default dreamscape context.

This factory is separate from the micro-factory used by the SystemLoader.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from core.memory.utils import load_memory_file
from core.interfaces.IDreamscapeService import IDreamscapeService

logger = logging.getLogger("DreamscapeGenerationFactory")


class DreamscapeGenerationFactory:
    def __init__(
        self,
        config_service: Any,
        chat_service: Any,
        response_handler: Any,
        discord_service: Optional[Any] = None,
        logger_instance: Optional[logging.Logger] = None
    ):
        self.config = config_service
        self.chat_service = chat_service
        self.response_handler = response_handler
        self.discord_service = discord_service
        self.logger = logger_instance or logger

    def create(self) -> IDreamscapeService:
        """
        Create and return a DreamscapeGenerationService instance
        with loaded memory and proper output handling.
        """
        try:
            output_dir = self._resolve_output_dir()
            memory_file = self._resolve_memory_file()
            memory_data = self._load_or_initialize_memory(memory_file)

            from core.services.dreamscape_generator_service import DreamscapeGenerationService

            return DreamscapeGenerationService(
                config_service=self.config,
                chat_service=self.chat_service,
                response_handler=self.response_handler,
                discord_service=self.discord_service,
                logger=self.logger,
                memory_data=memory_data
            )

        except Exception as e:
            self.logger.error(f"❌ Failed to create DreamscapeGenerationService: {e}", exc_info=True)
            raise

    def _resolve_output_dir(self) -> str:
        path = self.config.get("dreamscape_output_dir", "outputs/dreamscape")
        if hasattr(path, "get_path"):
            path = path.get_path()
        os.makedirs(path, exist_ok=True)
        return str(path)

    def _resolve_memory_file(self) -> str:
        path = self.config.get("dreamscape_memory_file", "memory/dreamscape_memory.json")
        if hasattr(path, "get_path"):
            path = path.get_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return str(path)

    def _load_or_initialize_memory(self, memory_file: str) -> dict:
        """
        Load existing dreamscape memory or create a default version if missing.
        """
        default_memory = {
            "last_updated": datetime.utcnow().isoformat(),
            "episode_count": 0,
            "themes": [],
            "characters": ["Victor the Architect"],
            "realms": ["The Dreamscape", "The Forge of Automation"],
            "artifacts": [],
            "recent_episodes": [],
            "skill_levels": {
                "System Convergence": 1,
                "Execution Velocity": 1,
                "Memory Integration": 1,
                "Protocol Design": 1,
                "Automation Engineering": 1
            },
            "architect_tier": {
                "current_tier": "Initiate Architect",
                "progress": "0%",
                "tier_history": []
            },
            "quests": {
                "completed": [],
                "active": ["Establish the Dreamscape"]
            },
            "protocols": [],
            "stabilized_domains": []
        }

        return load_memory_file(memory_file, default_memory)
