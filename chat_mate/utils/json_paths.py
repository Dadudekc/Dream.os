from chat_mate.core.PathManager import PathManager
import os

class JsonPaths:
    """
    Centralized configuration for all JSON file paths in the application.
    Uses PathManager to ensure consistent path resolution across the application.
    """
    
    @staticmethod
    def get_path(name: str) -> str:
        """Get the full path for a named JSON file."""
        pm = PathManager()
        
        # Configuration files
        if name == "config":
            return os.path.join(pm.get_path("config"), "config.json")
        elif name == "discord_config":
            return os.path.join(pm.get_path("config"), "discord_manager_config.json")
            
        # Memory files
        elif name == "memory_data":
            return os.path.join(pm.get_path("memory"), "memory_data.json")
        elif name == "persistent_memory":
            return os.path.join(pm.get_path("memory"), "persistent_memory.json")
        elif name == "project_analysis":
            return os.path.join(pm.get_path("memory"), "project_analysis.json")
        elif name == "unified_feedback":
            return os.path.join(pm.get_path("memory"), "unified_feedback.json")
        elif name == "system_state":
            return os.path.join(pm.get_path("memory"), "system_state.json")
            
        # Episode and cycle files
        elif name == "episode_counter":
            return os.path.join(pm.get_path("cycles"), "episode_counter.json")
        elif name == "dreamscape_episodes":
            return os.path.join(pm.get_path("dreamscape"), "dreamscape_episodes.json")
        elif name == "memory_updates":
            return os.path.join(pm.get_path("dreamscape"), "memory_updates.json")
        elif name == "episode_index":
            return os.path.join(pm.get_path("dreamscape"), "episode_index.json")
            
        # Template files
        elif name == "prompts":
            return os.path.join(pm.get_path("templates"), "prompts.json")
            
        else:
            raise ValueError(f"Unknown JSON path name: {name}") 
