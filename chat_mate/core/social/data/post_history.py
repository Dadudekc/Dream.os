from typing import Dict, List, Optional
from datetime import datetime
import json
import os

class PostHistory:
    def __init__(self, history_file: str = "data/post_history.json"):
        self.history_file = history_file
        self.history = self._load_history()
    
    def _load_history(self) -> List[Dict]:
        """Load post history from file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading post history: {e}")
                return []
        return []
    
    def _save_history(self):
        """Save post history to file."""
        try:
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=4)
        except Exception as e:
            print(f"Error saving post history: {e}")
    
    def add_post(self, post_data: Dict) -> bool:
        """Add a new post to history."""
        try:
            post_data["timestamp"] = datetime.now().isoformat()
            self.history.append(post_data)
            self._save_history()
            return True
        except Exception as e:
            print(f"Error adding post: {e}")
            return False
    
    def get_posts(self, limit: int = 10) -> List[Dict]:
        """Get recent posts from history."""
        return self.history[-limit:]
    
    def clear_history(self) -> bool:
        """Clear the post history."""
        try:
            self.history = []
            self._save_history()
            return True
        except Exception as e:
            print(f"Error clearing history: {e}")
            return False 