# micro_factories/dreamscape_factory.py

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from core.memory_utils import load_memory_file
from core.services.dreamscape_generator_service import DreamscapeGenerationService

class DreamscapeFactory:
    def __init__(
        self,
        config_service: Any,
        chat_service: Any,
        response_handler: Any,
        discord_service: Optional[Any] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.config = config_service
        self.chat_service = chat_service
        self.response_handler = response_handler
        self.discord_service = discord_service
        self.logger = logger or logging.getLogger("DreamscapeFactory")

    def create(self) -> DreamscapeGenerationService:
        try:
            output_dir = self._resolve_output_dir()
            memory_file = self._resolve_memory_file()
            memory_data = self._load_or_initialize_memory(memory_file)

            return DreamscapeGenerationService(
                config_service=self.config,
                chat_service=self.chat_service,
                response_handler=self.response_handler,
                discord_service=self.discord_service,
                logger=self.logger,
                memory_data=memory_data
            )
        except Exception as e:
            self.logger.error(f"Failed to create DreamscapeGeneratorService: {e}")
            raise

    def _resolve_output_dir(self) -> str:
        path = self.config.get("dreamscape_output_dir", "outputs/dreamscape")
        path = path.get_path() if hasattr(path, "get_path") else str(path)
        os.makedirs(path, exist_ok=True)
        return path

    def _resolve_memory_file(self) -> str:
        path = self.config.get("dreamscape_memory_file", "memory/dreamscape_memory.json")
        path = path.get_path() if hasattr(path, "get_path") else str(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def _load_or_initialize_memory(self, memory_file: str) -> dict:
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
