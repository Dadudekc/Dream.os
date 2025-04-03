"""
Core dreamscape generation service implementation.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from .interfaces import IDreamscapeService
from chat_mate.core.memory.context import ContextMemoryManager

logger = logging.getLogger(__name__)

class DreamscapeGenerationService(IDreamscapeService):
    """Service for generating dreamscape episodes."""

    def __init__(self, context_manager: Optional[ContextMemoryManager] = None):
        self.context_manager = context_manager or ContextMemoryManager()
        self.current_generation: Optional[Dict[str, Any]] = None
        self.output_dir = Path("outputs/dreamscape")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_episode(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a dreamscape episode from a prompt."""
        logger.info(f"Generating dreamscape episode with prompt: {prompt}")
        
        # Store context if provided
        if context:
            for key, value in context.items():
                self.context_manager.set_context(key, value)

        # Create episode data
        episode = {
            "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "prompt": prompt,
            "context": context or {},
            "status": "generating",
            "timestamp": datetime.now().isoformat(),
            "output": {}  # This would be filled with actual generation output
        }

        # Save episode
        self._save_episode(episode)
        self.current_generation = episode

        return episode

    def get_generation_status(self) -> Dict[str, Any]:
        """Get the current status of episode generation."""
        if not self.current_generation:
            return {"status": "idle"}
        return {
            "status": self.current_generation["status"],
            "episode_id": self.current_generation["id"]
        }

    def cancel_generation(self) -> bool:
        """Cancel the current episode generation."""
        if not self.current_generation:
            return False

        self.current_generation["status"] = "cancelled"
        self._save_episode(self.current_generation)
        self.current_generation = None
        return True

    def _save_episode(self, episode: Dict[str, Any]) -> None:
        """Save episode data to file."""
        episode_file = self.output_dir / f"episode_{episode['id']}.json"
        with open(episode_file, 'w', encoding='utf-8') as f:
            json.dump(episode, f, indent=2) 