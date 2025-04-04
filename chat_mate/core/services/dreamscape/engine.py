"""
Core dreamscape generation service implementation.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from .interfaces import IDreamscapeService
# Remove top-level import causing circular dependency
# from chat_mate.core.dreamscape.MemoryManager import MemoryManager 
from chat_mate.core.PathManager import PathManager
# REVIEW: Removed incorrect top-level import below
# from chat_mate.core.prompt_cycle.ContextMemoryManager import ContextMemoryManager

logger = logging.getLogger(__name__)

class DreamscapeGenerationService(IDreamscapeService):
    """Service for generating dreamscape episodes."""

    def __init__(self, context_manager: Optional[Any] = None): # Use Any temporarily for type hint
        # Remove the import from here - it's now handled by the package __init__
        # from chat_mate.core.dreamscape.MemoryManager import MemoryManager 
        
        # Need MemoryManager here, let's re-add top-level import temporarily OR rely on caller passing it
        # For now, assume caller might pass it, otherwise this init fails
        if not context_manager:
             # If not passed, we MUST import it here to instantiate
             # from ...dreamscape.MemoryManager import MemoryManager # REVIEW: Corrected import path 
             # REVIEW: Removed incorrect import below
             # from chat_mate.core.prompt_cycle.MemoryManager import MemoryManager 
             # from ...dreamscape.ContextMemoryManager import ContextMemoryManager # REVIEW: Switched back to absolute import
             # D:\overnight_scripts\chat_mate\core\memory\ContextMemoryManager.py 
             from core.memory.ContextMemoryManager import ContextMemoryManager
             # Get PathManager instance
             path_manager = PathManager()
             # Determine the output directory for context memory
             try:
                 memory_output_dir = path_manager.get_path('dreamscape_memory')
             except KeyError:
                 logger.warning("'dreamscape_memory' path key not found, using memory/dreamscape.")
                 memory_output_dir = path_manager.get_path('memory') / "dreamscape"
             memory_output_dir.mkdir(parents=True, exist_ok=True)
             
             # Instantiate ContextMemoryManager with the path
             self.context_manager = ContextMemoryManager(output_dir=str(memory_output_dir))
        else:
            # Use the provided one
            self.context_manager = context_manager
        
        # Get PathManager instance for output_dir
        path_manager = PathManager()
        # Get the general output dir for episodes using PathManager
        try:
            self.output_dir = path_manager.get_path('dreamscape') # Assumes 'dreamscape' key points to outputs/dreamscape
        except KeyError:
            logger.error("'dreamscape' path key not found for episode output. Defaulting.")
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