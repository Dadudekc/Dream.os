"""
Unified Memory Manager

This module provides the main MemoryManager class that combines:
- LRU caching + zlib compression for short-term memory
- JSON-based loading/saving with schema validation + backup on corruption
- SQLite-based long-term storage of interactions
- Conversation/interaction management
- Narrative generation via Jinja2 templates
"""

import os
import json
import zlib
import logging
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from cachetools import LRUCache
from jinja2 import Environment, FileSystemLoader

from .DatabaseManager import DatabaseManager
from .utils import load_memory_file, create_backup, validate_memory_structure
from core.recovery.agent_failure_hooks import AgentFailureHook

logger = logging.getLogger(__name__)

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
                 enable_wal: bool = True,
                 failure_hook: Optional[AgentFailureHook] = None):
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
            failure_hook: Optional AgentFailureHook instance for error handling.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.failure_hook = failure_hook

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

        # Register failure handlers if hook is provided
        if self.failure_hook:
            self._register_failure_handlers()

    def _register_failure_handlers(self):
        """Register failure handlers with the hook system."""
        if not self.failure_hook:
            return

        # Handler for memory corruption
        def handle_memory_corruption(error_type: str, context: Dict[str, Any]) -> bool:
            try:
                if error_type == "memory_corruption":
                    self.logger.warning("Attempting to recover from memory corruption...")
                    create_backup(Path(self.memory_file))
                    self._create_initial_memory()
                    self._save_memory()
                    return True
                return False
            except Exception as e:
                self.logger.error(f"Memory corruption handler failed: {e}")
                return False

        # Handler for cache issues
        def handle_cache_error(error_type: str, context: Dict[str, Any]) -> bool:
            try:
                if error_type == "cache_error":
                    self.logger.warning("Attempting to recover from cache error...")
                    self.cache.clear()
                    return True
                return False
            except Exception as e:
                self.logger.error(f"Cache error handler failed: {e}")
                return False

        # Register handlers
        self.failure_hook.register_handler(
            agent_name="memory_manager",
            handler=handle_memory_corruption,
            error_types=["memory_corruption"]
        )
        self.failure_hook.register_handler(
            agent_name="memory_manager",
            handler=handle_cache_error,
            error_types=["cache_error"]
        )

    def _load_memory(self):
        """Load memory from file or initialize if not present/invalid."""
        try:
            default_memory = self._create_initial_memory()
            self.data = load_memory_file(self.memory_file, default_memory)
            return self.data
        except Exception as e:
            error_context = {
                "file_path": self.memory_file,
                "error": str(e)
            }
            if self.failure_hook:
                if self.failure_hook.handle_failure("memory_manager", "memory_corruption", error_context):
                    # Retry after recovery
                    self.data = load_memory_file(self.memory_file, self._create_initial_memory())
                    return self.data
            raise

    def _create_initial_memory(self) -> Dict[str, Any]:
        """Create initial memory structure."""
        return {
            "metadata": {
                "version": "1.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_optimized": None
            },
            "segments": {
                "prompts": {},
                "feedback": {},
                "context": {},
                "system": {},
                "interactions": {}
            }
        }

    def _save_memory(self):
        """Save memory to file with proper formatting."""
        with self._lock:
            try:
                with open(self.memory_file, 'w') as f:
                    json.dump(self.data, f, indent=2)
            except Exception as e:
                error_context = {
                    "file_path": self.memory_file,
                    "error": str(e)
                }
                if self.failure_hook:
                    if not self.failure_hook.handle_failure("memory_manager", "memory_corruption", error_context):
                        create_backup(Path(self.memory_file))
                        raise
                else:
                    create_backup(Path(self.memory_file))
                    raise

    def set(self, key: str, data: Any, segment: str = "system") -> None:
        """Set a value in memory with compression."""
        if segment not in self.memory_segments:
            raise ValueError(f"Invalid segment: {segment}")
        
        with self._lock:
            try:
                # Compress and store data
                compressed = zlib.compress(json.dumps(data).encode())
                self.memory_segments[segment][key] = compressed
                
                # Update cache
                cache_key = f"{segment}:{key}"
                self.cache[cache_key] = data
                
                # Save segment
                self._save_segment(segment)
            except Exception as e:
                error_context = {
                    "key": key,
                    "segment": segment,
                    "error": str(e)
                }
                if self.failure_hook:
                    if not self.failure_hook.handle_failure("memory_manager", "cache_error", error_context):
                        self.logger.error(f"Failed to set memory key {key}: {e}")
                        raise
                else:
                    self.logger.error(f"Failed to set memory key {key}: {e}")
                    raise

    def get(self, key: str, segment: str = "system") -> Optional[Any]:
        """Get a value from memory, using cache when available."""
        if segment not in self.memory_segments:
            raise ValueError(f"Invalid segment: {segment}")
        
        cache_key = f"{segment}:{key}"
        
        # Try cache first
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Fall back to compressed storage
        with self._lock:
            try:
                if key in self.memory_segments[segment]:
                    compressed = self.memory_segments[segment][key]
                    data = json.loads(zlib.decompress(compressed).decode())
                    self.cache[cache_key] = data
                    return data
            except Exception as e:
                error_context = {
                    "key": key,
                    "segment": segment,
                    "error": str(e)
                }
                if self.failure_hook:
                    if self.failure_hook.handle_failure("memory_manager", "cache_error", error_context):
                        # Retry after recovery
                        return self.get(key, segment)
                self.logger.error(f"Failed to get memory key {key}: {e}")
                
        return None

    def delete(self, key: str, segment: str = "system") -> bool:
        """Delete a value from memory."""
        if segment not in self.memory_segments:
            raise ValueError(f"Invalid segment: {segment}")
        
        with self._lock:
            try:
                # Remove from compressed storage
                if key in self.memory_segments[segment]:
                    del self.memory_segments[segment][key]
                    
                    # Remove from cache
                    cache_key = f"{segment}:{key}"
                    if cache_key in self.cache:
                        del self.cache[cache_key]
                    
                    # Save segment
                    self._save_segment(segment)
                    return True
            except Exception as e:
                error_context = {
                    "key": key,
                    "segment": segment,
                    "error": str(e)
                }
                if self.failure_hook:
                    if self.failure_hook.handle_failure("memory_manager", "cache_error", error_context):
                        # Retry after recovery
                        return self.delete(key, segment)
                self.logger.error(f"Failed to delete memory key {key}: {e}")
                
        return False

    def clear_segment(self, segment: str) -> None:
        """Clear an entire memory segment."""
        if segment not in self.memory_segments:
            raise ValueError(f"Invalid segment: {segment}")
        
        with self._lock:
            try:
                # Clear segment data
                self.memory_segments[segment].clear()
                
                # Clear cache entries for this segment
                segment_prefix = f"{segment}:"
                cache_keys = [k for k in self.cache.keys() if k.startswith(segment_prefix)]
                for key in cache_keys:
                    del self.cache[key]
                    
                # Save empty segment
                self._save_segment(segment)
            except Exception as e:
                error_context = {
                    "segment": segment,
                    "error": str(e)
                }
                if self.failure_hook:
                    if not self.failure_hook.handle_failure("memory_manager", "cache_error", error_context):
                        self.logger.error(f"Failed to clear segment {segment}: {e}")
                        raise
                else:
                    self.logger.error(f"Failed to clear segment {segment}: {e}")
                    raise

    def get_segment_keys(self, segment: str) -> List[str]:
        """Get all keys in a memory segment."""
        if segment not in self.memory_segments:
            raise ValueError(f"Invalid segment: {segment}")
        return list(self.memory_segments[segment].keys())

    def get_segment_size(self, segment: str) -> int:
        """Get the number of items in a memory segment."""
        if segment not in self.memory_segments:
            raise ValueError(f"Invalid segment: {segment}")
        return len(self.memory_segments[segment])

    def optimize(self) -> None:
        """Optimize memory usage and storage."""
        with self._lock:
            try:
                # Clear cache
                self.cache.clear()
                
                # Recompress all segments
                for segment in self.memory_segments:
                    for key, compressed in list(self.memory_segments[segment].items()):
                        # Decompress and recompress to optimize storage
                        data = json.loads(zlib.decompress(compressed).decode())
                        self.memory_segments[segment][key] = zlib.compress(
                            json.dumps(data).encode(),
                            level=9  # Maximum compression
                        )
                
                # Update optimization timestamp
                self.data["metadata"]["last_optimized"] = datetime.now(timezone.utc).isoformat()
                self._save_memory()
                
                self.logger.info("Memory optimization complete")
            except Exception as e:
                self.logger.error(f"Failed to optimize memory: {e}")
                raise

    def get_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        stats = {
            "cache_size": len(self.cache),
            "cache_maxsize": self.cache.maxsize,
            "segments": {},
            "metadata": self.data.get("metadata", {})
        }
        
        for segment in self.memory_segments:
            segment_size = sum(len(compressed) for compressed in self.memory_segments[segment].values())
            stats["segments"][segment] = {
                "items": len(self.memory_segments[segment]),
                "size_bytes": segment_size
            }
        
        return stats

    def close(self):
        """Clean up resources."""
        self._save_memory()
        self.db_manager.close()
        self.cache.clear() 