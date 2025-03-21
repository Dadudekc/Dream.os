import os
import json
import zlib
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from cachetools import LRUCache
from core.PathManager import PathManager  # Assumes a module that provides a memory_dir attribute.
from core.UnifiedLoggingAgent import UnifiedLoggingAgent

logger = logging.getLogger(__name__)


class UnifiedMemoryManager:
    """
    UnifiedMemoryManager:
    Combines features from a basic MemoryManager (interaction recording, conversation lifecycle,
    and user history retrieval) with an optimized memory manager supporting:
      - LRU caching
      - Data compression
      - Thread-safe operations
      - Automatic memory pruning and optimization

    Memory is segmented by context. In addition to the system segments, we include
    a dedicated "interactions" segment to store conversation logs, user interactions,
    and conversation metadata.
    """

    def __init__(self, max_cache_size: int = 500, memory_dir: Optional[str] = None):
        """
        Args:
            max_cache_size: Maximum number of items to keep in the LRU cache.
            memory_dir: Optional override for the memory directory; otherwise from PathManager.
        """
        # Set up LRU cache
        self.cache = LRUCache(maxsize=max_cache_size)
        self._lock = threading.Lock()
        self.logger = UnifiedLoggingAgent()

        # Set up memory segments. We add "interactions" for conversation data.
        self.memory_segments: Dict[str, Dict[str, bytes]] = {
            "prompts": {},
            "feedback": {},
            "context": {},
            "system": {},
            "interactions": {}  # This segment holds user interactions and conversation data.
        }

        # Setup memory directory
        self.memory_dir = memory_dir or PathManager.memory_dir
        os.makedirs(self.memory_dir, exist_ok=True)

        # Load existing segments from disk.
        self._load_memory_segments()

    # --------------------------------------------------
    # Optimized Storage Methods (Caching, Compression)
    # --------------------------------------------------

    def set(self, key: str, data: Any, segment: str = "system") -> None:
        """
        Store data (JSON-serializable) with compression in the specified memory segment.
        """
        with self._lock:
            try:
                json_str = json.dumps(data)
                compressed = zlib.compress(json_str.encode('utf-8'))
                cache_key = f"{segment}:{key}"
                self.cache[cache_key] = compressed
                self.memory_segments.setdefault(segment, {})[key] = compressed
                self._save_segment(segment)
                self.logger.log_system_event(
                    event_type="memory_write",
                    message=f"Stored data in {segment}:{key}",
                    metadata={"segment": segment, "key": key}
                )
            except Exception as e:
                self.logger.log_system_event(
                    event_type="memory_error",
                    message=f"Error storing data: {str(e)}",
                    level="error"
                )

    def get(self, key: str, segment: str = "system") -> Optional[Any]:
        """
        Retrieve data from the cache or segment storage.
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
            self.logger.log_system_event(
                event_type="memory_error",
                message=f"Error retrieving data: {str(e)}",
                level="error"
            )
            return None

    def delete(self, key: str, segment: str = "system") -> bool:
        """
        Delete data from both cache and storage.
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
                self.logger.log_system_event(
                    event_type="memory_error",
                    message=f"Error deleting data: {str(e)}",
                    level="error"
                )
                return False

    def clear_segment(self, segment: str) -> None:
        """
        Clear an entire memory segment.
        """
        with self._lock:
            self.memory_segments.setdefault(segment, {}).clear()
            cache_keys = [k for k in self.cache.keys() if k.startswith(f"{segment}:")]
            for key in cache_keys:
                del self.cache[key]
            self._save_segment(segment)

    def get_segment_keys(self, segment: str) -> List[str]:
        """
        Get all keys in a memory segment.
        """
        return list(self.memory_segments.get(segment, {}).keys())

    def get_segment_size(self, segment: str) -> int:
        """
        Get the number of items in a memory segment.
        """
        return len(self.memory_segments.get(segment, {}))

    def _load_memory_segments(self) -> None:
        """
        Load all memory segments from disk.
        """
        for segment in self.memory_segments:
            segment_file = os.path.join(self.memory_dir, f"{segment}_memory.json")
            if os.path.exists(segment_file):
                try:
                    with open(segment_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Compress each value back into bytes.
                        self.memory_segments[segment] = {
                            k: zlib.compress(json.dumps(v).encode('utf-8'))
                            for k, v in data.items()
                        }
                except Exception as e:
                    self.logger.log_system_event(
                        event_type="memory_error",
                        message=f"Error loading segment {segment}: {str(e)}",
                        level="error"
                    )

    def _save_segment(self, segment: str) -> None:
        """
        Save a memory segment to disk.
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
            self.logger.log_system_event(
                event_type="memory_error",
                message=f"Error saving segment {segment}: {str(e)}",
                level="error"
            )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory manager statistics.
        """
        stats = {
            "cache_size": len(self.cache),
            "cache_maxsize": self.cache.maxsize,
            "segments": {}
        }
        for segment, data in self.memory_segments.items():
            segment_size = len(data)
            stats["segments"][segment] = {
                "items": segment_size,
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
                        self.logger.log_system_event(
                            event_type="memory_error",
                            message=f"Error optimizing {segment}:{key}: {str(e)}",
                            level="error"
                        )
                self.memory_segments[segment] = optimized_data
                self._save_segment(segment)
            self.logger.log_system_event(
                event_type="memory_optimized",
                message="Memory optimization completed",
                metadata=self.get_stats()
            )

    # --------------------------------------------------
    # Interaction Recording and Conversation Management
    # (Features from the basic MemoryManager)
    # --------------------------------------------------

    def record_interaction(
        self,
        platform: str,
        username: str,
        response: str,
        sentiment: str,
        success: bool,
        interaction_id: Optional[str] = None,
        chatgpt_url: Optional[str] = None
    ):
        """
        Record an interaction at both the platform/user level and conversation level.
        Stored in the "interactions" segment.
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
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
        # Key by a unique identifier (could use timestamp+username)
        key = f"{username}_{timestamp}"
        self.set(key, interaction_record, segment="interactions")

        # For conversation-level indexing, if an interaction_id is provided,
        # we store it as part of a conversation list.
        if interaction_id:
            conv_key = f"conversation_{interaction_id}"
            conversation = self.get(conv_key, segment="interactions") or []
            conversation.append(interaction_record)
            self.set(conv_key, conversation, segment="interactions")

    def initialize_conversation(self, interaction_id: str, metadata: Dict[str, Any]):
        """
        Initialize a conversation with metadata.
        """
        conv_meta_key = f"conversation_{interaction_id}_metadata"
        if self.get(conv_meta_key, segment="interactions") is None:
            conversation_metadata = {
                "initialized_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "metadata": metadata
            }
            self.set(conv_meta_key, conversation_metadata, segment="interactions")

    def retrieve_conversation(self, interaction_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all interactions belonging to a conversation.
        """
        conv_key = f"conversation_{interaction_id}"
        return self.get(conv_key, segment="interactions") or []

    def export_conversation_for_finetuning(self, interaction_id: str, export_path: str) -> bool:
        """
        Export conversation data for fine-tuning. Each interaction is transformed
        into a message pair for further processing.
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
            self.logger.log_system_event(
                event_type="export_error",
                message=f"Error exporting conversation: {str(e)}",
                level="error"
            )
            return False

    def get_user_history(self, platform: str, username: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve the latest interactions for a user on a given platform.
        """
        # Iterate through the "interactions" segment and filter by platform and username.
        history = []
        for compressed in self.memory_segments.get("interactions", {}).values():
            try:
                record = json.loads(zlib.decompress(compressed).decode('utf-8'))
                if record.get("platform") == platform and record.get("username") == username:
                    history.append(record)
            except Exception:
                continue
        # Sort by timestamp (most recent last)
        history.sort(key=lambda x: x.get("timestamp", ""))
        return history[-limit:]

    def user_sentiment_summary(self, platform: str, username: str) -> Dict[str, Any]:
        """
        Summarize sentiment and success statistics for a user's interactions.
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
        Clear a specific user's interaction history.
        """
        keys_to_delete = []
        for key, compressed in self.memory_segments.get("interactions", {}).items():
            try:
                record = json.loads(zlib.decompress(compressed).decode('utf-8'))
                if record.get("platform") == platform and record.get("username") == username:
                    keys_to_delete.append(key)
            except Exception:
                continue
        for key in keys_to_delete:
            self.delete(key, segment="interactions")

    def clear_platform_history(self, platform: str):
        """
        Clear all interaction history for a given platform.
        """
        keys_to_delete = []
        for key, compressed in self.memory_segments.get("interactions", {}).items():
            try:
                record = json.loads(zlib.decompress(compressed).decode('utf-8'))
                if record.get("platform") == platform:
                    keys_to_delete.append(key)
            except Exception:
                continue
        for key in keys_to_delete:
            self.delete(key, segment="interactions")