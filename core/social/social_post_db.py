import json
import os
from datetime import datetime
from typing import List, Dict, Optional


class SocialPostDatabase:
    """
    Manages the queue of social media posts.
    Tracks pending, posted, and failed posts in a JSON database.
    Also integrates with a persistent memory system to store global context.
    """
    
    def __init__(self, db_file: str = "social/data/post_queue.json", memory_file: str = "social/data/task_memory.json"):
        self.db_file = db_file
        self.memory_file = memory_file
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        self.data: Dict[str, List[Dict]] = {
            "queue": [],
            "posted": [],
            "failed": []
        }
        self.memory: Dict = {}  # Global persistent memory
        self._load()
        self._load_memory()

    def _load(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            print(f"✅ Loaded {len(self.data.get('queue', []))} tasks from {self.db_file}")
        else:
            print(f"📂 No existing database found. Starting fresh at {self.db_file}")

    def _save(self):
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)
        print(f"💾 Database saved: {self.db_file}")

    def _load_memory(self):
        if os.path.exists(self.memory_file):
            with open(self.memory_file, "r", encoding="utf-8") as f:
                self.memory = json.load(f)
            print(f"✅ Loaded persistent memory from {self.memory_file}")
        else:
            print(f"📂 No existing memory file found. Starting with empty memory.")
            self.memory = {}

    def _save_memory(self):
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=4)
        print(f"💾 Persistent memory saved: {self.memory_file}")

    def update_memory(self, key: str, value):
        """
        Update or add a memory key/value pair.
        """
        self.memory[key] = value
        self._save_memory()
        print(f"🔄 Updated memory: {key} = {value}")

    def get_memory(self, key: str):
        """
        Retrieve a value from persistent memory.
        """
        return self.memory.get(key)

    def add_to_queue(self, post: Dict):
        self.data["queue"].append(post)
        self._save()
        print(f"📥 Enqueued post: {post.get('title', 'Untitled')}")

    def mark_posted(self, post: Dict):
        if post in self.data["queue"]:
            self.data["queue"].remove(post)
        self.data["posted"].append(post)
        self._save()
        print(f"✅ Marked post as posted: {post.get('title', 'Untitled')}")

    def mark_failed(self, post: Dict):
        if post in self.data["queue"]:
            self.data["queue"].remove(post)
        self.data["failed"].append(post)
        self._save()
        print(f"❌ Marked post as failed: {post.get('title', 'Untitled')}")

    def get_next_post(self) -> Optional[Dict]:
        if self.data["queue"]:
            next_post = self.data["queue"][0]
            print(f"➡️ Next post: {next_post.get('title', 'Untitled')}")
            return next_post
        print("🚫 No posts left in queue.")
        return None

    def get_queue_length(self) -> int:
        length = len(self.data["queue"])
        print(f"📊 Queue length: {length}")
        return length
