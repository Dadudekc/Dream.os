import os
import json
import zlib
import logging
import shutil
import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from cachetools import LRUCache
from jinja2 import Environment, FileSystemLoader
from .memory_utils import load_memory_file

###############################################################################
# Database Manager for Long-Term Storage
###############################################################################
class DatabaseManager:
    """
    DatabaseManager stores interactions and conversation metadata for
    long-term retention using SQLite.
    """

    def __init__(self, db_file: str = "memory/engagement_memory.db", wal_mode: bool = True):
        """
        Args:
            db_file: Path to the SQLite database file.
            wal_mode: If True, enable Write-Ahead Logging for better concurrency.
        """
        self.db_file = db_file
        self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        
        if wal_mode:
            # Enable WAL mode for better concurrent reads/writes
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.close()
        
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
        """
        Insert a single interaction record into the database.
        """
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
        """
        Store conversation metadata if it does not already exist.
        """
        c = self.conn.cursor()
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        c.execute("""
            INSERT OR IGNORE INTO conversations_metadata (interaction_id, initialized_at, metadata)
            VALUES (?, ?, ?)
        """, (interaction_id, timestamp, json.dumps(metadata)))
        self.conn.commit()

    def get_conversation(self, interaction_id: str) -> List[Dict[str, Any]]:
        """
        Return all interactions with a given interaction_id from earliest to latest.
        """
        c = self.conn.cursor()
        c.execute("""
            SELECT 
                platform, username, interaction_id, timestamp, response, sentiment, success, chatgpt_url
            FROM interactions
            WHERE interaction_id = ?
            ORDER BY timestamp ASC
        """, (interaction_id,))
        rows = c.fetchall()
        columns = ["platform", "username", "interaction_id", "timestamp", "response", "sentiment", "success", "chatgpt_url"]
        return [dict(zip(columns, row)) for row in rows]

    def close(self):
        """
        Close the database connection.
        """
        self.conn.close()


###############################################################################
# Unified Memory Manager
###############################################################################
class MemoryManager:
    """
    MemoryManager combines:
      - LRU caching + zlib compression for short-term memory
      - JSON-based loading/saving with schema validation + backup on corruption
      - SQLite-based long-term storage of interactions
      - Conversation/interaction management
      - Narrative generation via Jinja2 templates
    """

    def __init__(self,
                 max_cache_size: int = 500,
                 memory_dir: Optional[str] = None,
                 memory_file: str = "memory/engagement_memory.json",
                 db_file: str = "memory/engagement_memory.db",
                 template_dir: str = "templates",
                 logger: Optional[logging.Logger] = None,
                 enable_wal: bool = True):
        """
        Initialize the MemoryManager.

        Args:
            max_cache_size: Maximum size of the LRU cache.
            memory_dir: Directory for saving memory segments.
            memory_file: Path to the main JSON memory file.
            db_file: Path to the SQLite database file.
            template_dir: Directory containing Jinja2 templates.
            logger: Optional logger instance. If None, creates a default.
            enable_wal: If True, enable WAL mode in SQLite for concurrency.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Setup memory directory
        self.memory_dir = memory_dir or os.path.join(os.getcwd(), "memory")
        os.makedirs(self.memory_dir, exist_ok=True)
        self.memory_file = memory_file

        # Setup concurrency lock and LRU cache
        self._lock = threading.Lock()
        self.cache = LRUCache(maxsize=max_cache_size)

        # Memory segments for in-memory JSON (with compression)
        self.memory_segments: Dict[str, Dict[str, bytes]] = {
            "prompts": {},
            "feedback": {},
            "context": {},
            "system": {},
            "interactions": {}
        }

        # Initialize data dict (high-level structure from memory_file)
        self.data = {}
        self._load_memory()

        # Initialize database manager
        self.db_manager = DatabaseManager(db_file=db_file, wal_mode=enable_wal)

        # Initialize Jinja2 environment for narratives
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )

    ############################################################################
    # JSON Memory: Load, Save, Validation, Backup
    ############################################################################
    def _load_memory(self):
        """Load memory from file or initialize if not present/invalid."""
        default_memory = self._create_initial_memory()
        self.data = load_memory_file(self.memory_file, default_memory)
        return self.data

    def _backup_corrupted_file(self, file_path: str) -> None:
        """Create a backup of a corrupted file with timestamp."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{file_path}.{timestamp}.bak"
            shutil.copy2(file_path, backup_path)
            self.logger.info(f"Created backup of corrupted file at: {backup_path}")
        except Exception as e:
            self.logger.error(f"Failed to create backup of corrupted file: {str(e)}")

    def _create_initial_memory(self) -> Dict[str, Any]:
        """Create initial memory structure."""
        return {
            "last_updated": datetime.now().isoformat(),
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

    def _save_memory(self):
        """
        Internal method to save the top-level memory dictionary to JSON,
        with validation and backup of any existing file.
        """
        file_path = Path(self.memory_file)
        try:
            self._validate_memory(self.data)  # Validate before saving
            if file_path.exists():
                self._backup_file(file_path)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving memory to {file_path}: {str(e)}")

    def _validate_memory(self, memory_data: Dict[str, Any]) -> None:
        """
        Validate the memory structure; raise ValueError if invalid.
        Extend this method with schema checks as needed.
        """
        if not isinstance(memory_data, dict):
            raise ValueError("Memory must be a dictionary.")

    def _backup_file(self, file_path: Path):
        """
        Backup the specified file by copying it to <filename>.bak
        """
        try:
            backup_path = file_path.with_suffix('.bak')
            shutil.copy(file_path, backup_path)
            self.logger.info(f"Backup created for {file_path} at {backup_path}")
        except Exception as e:
            self.logger.error(f"Error backing up file {file_path}: {str(e)}")

    ############################################################################
    # Compressed Segment Storage
    ############################################################################
    def set(self, key: str, data: Any, segment: str = "system") -> None:
        """
        Store JSON-serializable data with compression in a memory segment.
        """
        with self._lock:
            try:
                json_str = json.dumps(data)
                compressed = zlib.compress(json_str.encode('utf-8'))
                cache_key = f"{segment}:{key}"

                # Update in-memory segment
                self.cache[cache_key] = compressed
                self.memory_segments.setdefault(segment, {})[key] = compressed

                # Persist segment to disk
                self._save_segment(segment)

                self.logger.info(f"Stored data in {segment}:{key}")
            except Exception as e:
                self.logger.error(f"Error storing data in {segment}:{key} - {e}")

    def get(self, key: str, segment: str = "system") -> Optional[Any]:
        """
        Retrieve data from a memory segment (cache or fallback to disk).
        """
        cache_key = f"{segment}:{key}"
        try:
            if cache_key in self.cache:
                compressed = self.cache[cache_key]
            else:
                compressed = self.memory_segments.get(segment, {}).get(key, None)
                if compressed:
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
        Delete a key from both cache and segment storage.
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
        Clear all items in a memory segment.
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
        Save a single memory segment to a file (JSON) in uncompressed form.
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

    def optimize(self) -> None:
        """
        Recompress all segments at max compression and clear the cache.
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

    def get_stats(self) -> Dict[str, Any]:
        """
        Return statistics on cache usage and memory segment sizes.
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

    ############################################################################
    # JSON Memory: Higher-level platform/user manipulation
    ############################################################################
    def get_user_history(self, platform: str, username: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve the latest interactions for a given user on a given platform
        from the in-memory JSON data.
        """
        platform_data = self.data.get("platforms", {})
        user_history = platform_data.get(platform, {}).get(username, [])
        return user_history[-limit:]

    def clear_user_history(self, platform: str, username: str):
        """
        Clear a specific user's history from the top-level JSON memory.
        """
        platform_users = self.data.get("platforms", {}).get(platform, {})
        if username in platform_users:
            del platform_users[username]
            self._save_memory()

    def clear_platform_history(self, platform: str):
        """
        Clear all user history for a given platform in the top-level JSON memory.
        """
        if platform in self.data.get("platforms", {}):
            del self.data["platforms"][platform]
            self._save_memory()

    ############################################################################
    # Interaction & Conversation Recording
    ############################################################################
    def record_interaction(self,
                           platform: str,
                           username: str,
                           response: str,
                           sentiment: str,
                           success: bool,
                           interaction_id: Optional[str] = None,
                           chatgpt_url: Optional[str] = None):
        """
        Record an interaction in short-term segments AND long-term DB.
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

        # Insert into LRU + segment
        unique_key = f"{username}_{timestamp}"
        self.set(unique_key, interaction_record, segment="interactions")

        # If part of a conversation, update the conversation segment
        if interaction_id:
            conv_key = f"conversation_{interaction_id}"
            conversation = self.get(conv_key, segment="interactions") or []
            conversation.append(interaction_record)
            self.set(conv_key, conversation, segment="interactions")

        # Also write to DB
        self.db_manager.record_interaction(interaction_record)

        # Optionally track user interactions in top-level JSON
        self._track_user_interaction(platform, username, interaction_record)

    def initialize_conversation(self, interaction_id: str, metadata: Dict[str, Any]):
        """
        Initialize a conversation with metadata, stored both in segments and DB.
        """
        conv_meta_key = f"conversation_{interaction_id}_metadata"
        if self.get(conv_meta_key, segment="interactions") is None:
            conversation_metadata = {
                "initialized_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "metadata": metadata
            }
            self.set(conv_meta_key, conversation_metadata, segment="interactions")
        # DB record
        self.db_manager.initialize_conversation(interaction_id, metadata)

    def retrieve_conversation(self, interaction_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve a conversation by its interaction_id from the DB.
        """
        return self.db_manager.get_conversation(interaction_id)

    def export_conversation_for_finetuning(self, interaction_id: str, export_path: str) -> bool:
        """
        Export a conversation to a file in a structure suitable for fine-tuning.
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

    def user_sentiment_summary(self, platform: str, username: str) -> Dict[str, Any]:
        """
        Summarize sentiment distribution and success rate for a user.
        """
        history = self.get_user_history(platform, username, limit=50)
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        success_count = 0

        for interaction in history:
            sentiment = interaction.get("sentiment", "neutral")
            if sentiment not in sentiment_counts:
                sentiment_counts[sentiment] = 0
            sentiment_counts[sentiment] += 1
            if interaction.get("success"):
                success_count += 1

        total_interactions = len(history)
        success_rate = (success_count / total_interactions * 100) if total_interactions else 0.0

        return {
            "total_interactions": total_interactions,
            "sentiment_distribution": sentiment_counts,
            "success_rate_percent": round(success_rate, 2)
        }

    ############################################################################
    # Low-level user interaction tracking in the top-level JSON data
    ############################################################################
    def _track_user_interaction(self, platform: str, username: str, record: Dict[str, Any]) -> None:
        """
        Insert the record into the top-level JSON memory for the user.
        """
        platforms = self.data.setdefault("platforms", {})
        platform_data = platforms.setdefault(platform, {})
        user_history = platform_data.setdefault(username, [])
        user_history.append(record)
        self._save_memory()

    ############################################################################
    # Jinja2 Narrative Generation
    ############################################################################
    def generate_narrative(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a narrative using the specified Jinja2 template and context.
        """
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            self.logger.error(f"Error generating narrative with template {template_name} - {e}")
            return ""

    ############################################################################
    # Optional: Update Arbitrary Keys in the JSON Memory
    ############################################################################
    def update_context(self, key_path: str, value: Any) -> bool:
        """
        Update a nested key in the top-level 'self.data' using dot-notation.
        E.g., "system.config.value".
        """
        keys = key_path.split('.')
        current = self.data
        for key in keys[:-1]:
            if key not in current:
                self.logger.warning(f"Key '{key}' not found in memory. Cannot update.")
                return False
            current = current[key]
        current[keys[-1]] = value
        self._save_memory()
        return True

    ############################################################################
    # Close Resources
    ############################################################################
    def close(self):
        """
        Close any resources (e.g., database connection).
        """
        self.db_manager.close()


# Shared singleton instance
memory = MemoryManager()