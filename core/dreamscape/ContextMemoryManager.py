import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

class ContextMemoryManager:
    """
    Manages the loading, saving, and updating of Dreamscape context memory.
    Handles episode themes, skills, protocols, domains, and architect tier progression.
    """
    
    def __init__(self, output_dir: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the context memory manager.
        
        Args:
            output_dir: Directory where context memory file is stored
            logger: Optional logger instance
        """
        self.output_dir = output_dir
        self.logger = logger or logging.getLogger(__name__)
        self.context_file = os.path.join(output_dir, "dreamscape_context.json")
        self.context = self.load_context()
        
    def load_context(self) -> Dict[str, Any]:
        """
        Load context memory from file or initialize new context if file doesn't exist.
        
        Returns:
            Dictionary containing context data
        """
        try:
            if os.path.exists(self.context_file):
                with open(self.context_file, 'r', encoding='utf-8') as f:
                    context = json.load(f)
                self.logger.info("✅ Context memory loaded successfully")
                return context
        except Exception as e:
            self.logger.error(f"❌ Error loading context memory: {str(e)}")
            
        # Initialize new context if loading fails
        return self._initialize_new_context()
        
    def save_context(self) -> bool:
        """
        Save current context memory to file.
        
        Returns:
            True if save was successful, False otherwise
        """
        try:
            with open(self.context_file, 'w', encoding='utf-8') as f:
                json.dump(self.context, f, indent=2)
            self.logger.info("✅ Context memory saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error saving context memory: {str(e)}")
            return False
            
    def _initialize_new_context(self) -> Dict[str, Any]:
        """
        Create a new context memory structure with default values.
        
        Returns:
            Dictionary containing initialized context
        """
        return {
            "episode_count": 0,
            "last_updated": datetime.now().isoformat(),
            "recent_episodes": [],
            "skill_levels": {},
            "protocols": [],
            "stabilized_domains": [],
            "active_themes": [],
            "architect_tier": {
                "current_tier": "Initiate Architect",
                "progress": "0%"
            },
            "quests": {
                "active": [],
                "completed": []
            }
        }
        
    def update_with_episode(self, episode_text: str, episode_title: str) -> None:
        """
        Update context with information from a new episode.
        
        Args:
            episode_text: The full text of the generated episode
            episode_title: The title of the episode
        """
        # Extract themes and update context
        themes = self._extract_themes(episode_text)
        timestamp = datetime.now().isoformat()
        
        # Update episode count and recent episodes
        self.context["episode_count"] += 1
        self.context["recent_episodes"].append({
            "title": episode_title,
            "timestamp": timestamp,
            "themes": themes
        })
        
        # Keep only the 10 most recent episodes
        self.context["recent_episodes"] = self.context["recent_episodes"][-10:]
        
        # Update active themes
        self.context["active_themes"] = list(set(self.context["active_themes"] + themes))
        
        # Update other context elements
        self._update_skills(episode_text)
        self._update_protocols(episode_text)
        self._update_domains(episode_text)
        self._update_architect_tier(episode_text)
        self._update_quests(episode_text)
        
        # Update timestamp
        self.context["last_updated"] = timestamp
        
        # Save updated context
        self.save_context()
        
    def _extract_themes(self, text: str) -> List[str]:
        """
        Extract themes from episode text using pattern matching.
        
        Args:
            text: The episode text to analyze
            
        Returns:
            List of extracted themes
        """
        themes = []
        # Add theme extraction logic here
        # This could involve regex patterns, keyword matching, etc.
        return themes
        
    def _update_skills(self, text: str) -> None:
        """Update skill levels based on episode content."""
        # Add skill update logic here
        pass
        
    def _update_protocols(self, text: str) -> None:
        """Update protocols based on episode content."""
        # Add protocol update logic here
        pass
        
    def _update_domains(self, text: str) -> None:
        """Update stabilized domains based on episode content."""
        # Add domain update logic here
        pass
        
    def _update_architect_tier(self, text: str) -> None:
        """Update architect tier progress based on episode content."""
        # Add architect tier update logic here
        pass
        
    def _update_quests(self, text: str) -> None:
        """Update active and completed quests based on episode content."""
        # Add quest update logic here
        pass
        
    def get_context_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current context.
        
        Returns:
            Dictionary containing context summary
        """
        return self.context.copy()  # Return a copy to prevent accidental modifications 
