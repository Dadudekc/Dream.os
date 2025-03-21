import os
import json
import zlib
import logging
import threading
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from cachetools import LRUCache
from jinja2 import Environment, FileSystemLoader

# Configure module-level logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

###############################################################################
# Database Manager for Long-Term Storage
###############################################################################
class DatabaseManager:
    """
    DatabaseManager stores interactions and conversation metadata for
    long-term retention using SQLite.
    """

    def __init__(self, db_file: str = "memory/engagement_memory.db"):
        self.db_file = db_file
        self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        self._initialize_db()

    def _initialize_db(self):
        c = self.conn.cursor()
        # Create interactions table
        c.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                username TEXT,
                interaction_id TEXT,
                timestamp TEXT,
                response TEXT,
                sentiment TEXT,
                success INTEGER,
                chatgpt_url TEXT
            )
        """)
        # Create conversations metadata table
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversations_metadata (
                interaction_id TEXT PRIMARY KEY,
                initialized_at TEXT,
                metadata TEXT
            )
        """)
        self.conn.commit()

    def record_interaction(self, record: Dict[str, Any]):
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO interactions (
                platform, username, interaction_id, timestamp, response, sentiment, success, chatgpt_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.get("platform"),
            record.get("username"),
            record.get("interaction_id"),
            record.get("timestamp"),
            record.get("response"),
            record.get("sentiment"),
            1 if record.get("success") else 0,
            record.get("chatgpt_url")
        ))
        self.conn.commit()

    def initialize_conversation(self, interaction_id: str, metadata: Dict[str, Any]):
        c = self.conn.cursor()
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        c.execute("""
            INSERT OR IGNORE INTO conversations_metadata (interaction_id, initialized_at, metadata)
            VALUES (?, ?, ?)
        """, (interaction_id, timestamp, json.dumps(metadata)))
        self.conn.commit()

    def get_conversation(self, interaction_id: str) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute("""
            SELECT platform, username, interaction_id, timestamp, response, sentiment, success, chatgpt_url 
            FROM interactions
            WHERE interaction_id = ?
            ORDER BY timestamp ASC
        """, (interaction_id,))
        rows = c.fetchall()
        columns = ["platform", "username", "interaction_id", "timestamp", "response", "sentiment", "success", "chatgpt_url"]
        return [dict(zip(columns, row)) for row in rows]

    def close(self):
        self.conn.close()


###############################################################################
# Unified Memory Manager (In-Memory + DB + Narrative)
###############################################################################
class UnifiedMemoryManager:
    """
    UnifiedMemoryManager combines features from an optimized memory manager with:
      - LRU caching and data compression (for fast short-term storage)
      - JSON file storage for ephemeral memory
      - SQLite-based long-term storage of interactions
      - Conversation and interaction management
      - Narrative generation via Jinja2 templates

    Memory is segmented by context (e.g. "system", "prompts", "interactions").
    """

    def __init__(self,
                 max_cache_size: int = 500,
                 memory_dir: Optional[str] = None,
                 memory_file: str = "memory/engagement_memory.json",
                 db_file: str = "memory/engagement_memory.db",
                 template_dir: str = "templates"):
        # Setup cache and lock
        self.cache = LRUCache(maxsize=max_cache_size)
        self._lock = threading.Lock()
        self.logger = logger  # Using module logger; can be replaced with a more advanced logging agent

        # Memory segments for JSON storage (with compression)
        self.memory_segments: Dict[str, Dict[str, bytes]] = {
            "prompts": {},
            "feedback": {},
            "context": {},
            "system": {},
            "interactions": {}  # Holds interaction records and conversation indexes
        }

        # Setup memory directory and file
        self.memory_dir = memory_dir or os.path.join(os.getcwd(), "memory")
        os.makedirs(self.memory_dir, exist_ok=True)
        self.memory_file = memory_file

        # Load existing JSON memory from file (if available)
        self.data = {}
        self._load_memory()

        # Initialize database manager for long-term storage
        self.db_manager = DatabaseManager(db_file)

        # Initialize Jinja2 environment for narrative generation
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir),
                                     trim_blocks=True,
                                     lstrip_blocks=True)

    # -----------------------------
    # JSON Memory Operations (with Compression)
    # -----------------------------
    def _load_memory(self):
        """Load memory data from JSON file and ensure integrity."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading memory file: {e}")
                self.data = {}
        else:
            self.data = {}
        # Ensure basic keys exist
        self.data.setdefault("platforms", {})
        self.data.setdefault("conversations", {})

    def _save_memory(self):
        """Save memory data to JSON file."""
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving memory file: {e}")

    # -----------------------------
    # Optimized Storage Methods (Caching & Compression for segments)
    # -----------------------------
    def set(self, key: str, data: Any, segment: str = "system") -> None:
        """
        Store JSON-serializable data with compression in a memory segment.
        """
        with self._lock:
            try:
                json_str = json.dumps(data)
                compressed = zlib.compress(json_str.encode('utf-8'))
                cache_key = f"{segment}:{key}"
                self.cache[cache_key] = compressed
                self.memory_segments.setdefault(segment, {})[key] = compressed
                self._save_segment(segment)
                self.logger.info(f"Stored data in {segment}:{key}")
            except Exception as e:
                self.logger.error(f"Error storing data in {segment}:{key} - {e}")

    def get(self, key: str, segment: str = "system") -> Optional[Any]:
        """
        Retrieve data from cache or memory segment storage.
        """
        cache_key = f"{segment}:{key}"
        try:
            if cache_key in self.cache:
                compressed = self.cache[cache_key]
            elif key in self.memory_segments.get(segment, {}):
                compressed = self.memory_segments[segment][key]
                self.cache[cache_key] = compressed
            else:
                return None

            json_str = zlib.decompress(compressed).decode('utf-8')
            return json.loads(json_str)
        except Exception as e:
            self.logger.error(f"Error retrieving {segment}:{key} - {e}")
            return None

    def delete(self, key: str, segment: str = "system") -> bool:
        """
        Delete a key from both cache and memory segment storage.
        """
        with self._lock:
            try:
                cache_key = f"{segment}:{key}"
                if cache_key in self.cache:
                    del self.cache[cache_key]
                if key in self.memory_segments.get(segment, {}):
                    del self.memory_segments[segment][key]
                    self._save_segment(segment)
                return True
            except Exception as e:
                self.logger.error(f"Error deleting {segment}:{key} - {e}")
                return False

    def clear_segment(self, segment: str) -> None:
        """
        Clear all keys in a memory segment.
        """
        with self._lock:
            self.memory_segments.setdefault(segment, {}).clear()
            keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{segment}:")]
            for key in keys_to_remove:
                del self.cache[key]
            self._save_segment(segment)

    def get_segment_keys(self, segment: str) -> List[str]:
        """
        Return all keys in a memory segment.
        """
        return list(self.memory_segments.get(segment, {}).keys())

    def get_segment_size(self, segment: str) -> int:
        """
        Return the number of items in a memory segment.
        """
        return len(self.memory_segments.get(segment, {}))

    def _save_segment(self, segment: str) -> None:
        """
        Save a specific memory segment to a file.
        Each segment is stored in a separate JSON file.
        """
        segment_file = os.path.join(self.memory_dir, f"{segment}_memory.json")
        try:
            decompressed_data = {}
            for k, v in self.memory_segments.get(segment, {}).items():
                json_str = zlib.decompress(v).decode('utf-8')
                decompressed_data[k] = json.loads(json_str)
            with open(segment_file, 'w', encoding='utf-8') as f:
                json.dump(decompressed_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving segment {segment} - {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Return statistics about the memory manager.
        """
        stats = {
            "cache_size": len(self.cache),
            "cache_maxsize": self.cache.maxsize,
            "segments": {}
        }
        for segment, data in self.memory_segments.items():
            stats["segments"][segment] = {
                "items": len(data),
                "compressed_size": sum(len(v) for v in data.values())
            }
        return stats

    def optimize(self) -> None:
        """
        Optimize memory usage by clearing the cache and recompressing data.
        """
        with self._lock:
            self.cache.clear()
            for segment, data in self.memory_segments.items():
                optimized_data = {}
                for key, compressed in data.items():
                    try:
                        json_str = zlib.decompress(compressed).decode('utf-8')
                        optimized_data[key] = zlib.compress(json_str.encode('utf-8'), level=9)
                    except Exception as e:
                        self.logger.error(f"Error optimizing {segment}:{key} - {e}")
                self.memory_segments[segment] = optimized_data
                self._save_segment(segment)
            self.logger.info("Memory optimization completed. Stats: " + json.dumps(self.get_stats()))

    # -----------------------------
    # Interaction Recording and Conversation Management
    # -----------------------------
    def record_interaction(self,
                           platform: str,
                           username: str,
                           response: str,
                           sentiment: str,
                           success: bool,
                           interaction_id: Optional[str] = None,
                           chatgpt_url: Optional[str] = None):
        """
        Record an interaction in both short-term JSON memory and long-term DB.
        Also indexes conversation if interaction_id is provided.
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        interaction_record = {
            "platform": platform,
            "username": username,
            "interaction_id": interaction_id,
            "timestamp": timestamp,
            "response": response,
            "sentiment": sentiment,
            "success": success,
            "chatgpt_url": chatgpt_url
        }
        # Generate a unique key (using username and timestamp)
        key = f"{username}_{timestamp}"
        self.set(key, interaction_record, segment="interactions")

        # If this interaction is part of a conversation, index it.
        if interaction_id:
            conv_key = f"conversation_{interaction_id}"
            conversation = self.get(conv_key, segment="interactions") or []
            conversation.append(interaction_record)
            self.set(conv_key, conversation, segment="interactions")

        # Record in database for long-term storage.
        self.db_manager.record_interaction(interaction_record)

    def initialize_conversation(self, interaction_id: str, metadata: Dict[str, Any]):
        """
        Initialize a conversation with metadata.
        Stores data in JSON memory and the database.
        """
        conv_meta_key = f"conversation_{interaction_id}_metadata"
        if self.get(conv_meta_key, segment="interactions") is None:
            conversation_metadata = {
                "initialized_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "metadata": metadata
            }
            self.set(conv_meta_key, conversation_metadata, segment="interactions")
        self.db_manager.initialize_conversation(interaction_id, metadata)

    def retrieve_conversation(self, interaction_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve a conversation by its interaction_id.
        Prefers the long-term DB data.
        """
        return self.db_manager.get_conversation(interaction_id)

    def export_conversation_for_finetuning(self, interaction_id: str, export_path: str) -> bool:
        """
        Export conversation data for fine-tuning.
        Each interaction is transformed into a message pair.
        """
        conversation = self.retrieve_conversation(interaction_id)
        if not conversation:
            return False

        fine_tuning_data = [
            {
                "messages": [
                    {"role": "user", "content": f"Interaction on {interaction['timestamp']}"},
                    {"role": "assistant", "content": interaction["response"]}
                ]
            } for interaction in conversation
        ]

        os.makedirs(os.path.dirname(export_path), exist_ok=True)
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                for entry in fine_tuning_data:
                    f.write(json.dumps(entry) + "\n")
            return True
        except Exception as e:
            self.logger.error(f"Error exporting conversation {interaction_id} - {e}")
            return False

    def get_user_history(self, platform: str, username: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve the latest interactions for a given user on a platform.
        This uses the in-memory JSON data.
        """
        user_history = self.data.get("platforms", {}).get(platform, {}).get(username, [])
        return user_history[-limit:]

    def user_sentiment_summary(self, platform: str, username: str) -> Dict[str, Any]:
        """
        Summarize sentiment and success statistics for a user.
        """
        history = self.get_user_history(platform, username, limit=50)
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        success_count = 0

        for interaction in history:
            sentiment = interaction.get("sentiment", "neutral")
            sentiment_counts[sentiment] += 1
            if interaction.get("success"):
                success_count += 1

        total_interactions = len(history)
        success_rate = (success_count / total_interactions) * 100 if total_interactions else 0

        return {
            "total_interactions": total_interactions,
            "sentiment_distribution": sentiment_counts,
            "success_rate_percent": round(success_rate, 2)
        }

    def clear_user_history(self, platform: str, username: str):
        """
        Clear a specific user's history from JSON memory.
        """
        platform_users = self.data.get("platforms", {}).get(platform, {})
        if username in platform_users:
            del platform_users[username]
            self._save_memory()

    def clear_platform_history(self, platform: str):
        """
        Clear all history for a given platform from JSON memory.
        """
        if platform in self.data.get("platforms", {}):
            del self.data["platforms"][platform]
            self._save_memory()

    # -----------------------------
    # Narrative Generation via Jinja2
    # -----------------------------
    def generate_narrative(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a narrative using a Jinja template.
        Example: 'dreamscape_template.txt' in the templates directory.
        """
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            self.logger.error(f"Error generating narrative with template {template_name} - {e}")
            return ""

    # -----------------------------
    # Close Resources
    # -----------------------------
    def close(self):
        """
        Close any resources held by the memory manager.
        """
        self.db_manager.close()


###############################################################################
# Example Usage
###############################################################################
if __name__ == "__main__":
    # Create an instance of the unified memory manager.
    mm = UnifiedMemoryManager()

    # Record an interaction.
    mm.record_interaction(
        platform="Discord",
        username="Victor",
        response="System audit complete. All systems are online.",
        sentiment="positive",
        success=True,
        interaction_id="audit_001",
        chatgpt_url="http://chat.openai.com/audit_001"
    )

    # Initialize a conversation.
    mm.initialize_conversation("audit_001", {"topic": "System Audit", "priority": "High"})

    # Generate a narrative using a Jinja template.
    context = {
        "audit_title": "SYSTEM AUDIT: Victor’s Current Workflow & Execution Model",
        "objective": "Generate $1M within 12 months",
        "system_state": "Detailed breakdown of trading, automation, and content pipelines.",
        "systemic_root_causes": "Fragmentation, isolation, and lack of feedback loops.",
        "surgical_optimizations": "Implement automated funnels, code modularity, and outreach strategies.",
        "priority_actions": "Define core offer, build free lead magnet, and automate distribution.",
        "conclusion": "Time to let the machines speak. FULL SYNC MODE ENGAGED.",
        "architect_tier_progression": 2
    }
    narrative = mm.generate_narrative("dreamscape_template.txt", context)
    print("Generated Narrative:")
    print(narrative)

    # Export the conversation for fine-tuning.
    if mm.export_conversation_for_finetuning("audit_001", "exports/audit_001.txt"):
        print("Conversation exported successfully.")
    else:
        print("Failed to export conversation.")

    # Close resources.
    mm.close()