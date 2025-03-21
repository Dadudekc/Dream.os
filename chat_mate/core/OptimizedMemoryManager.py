import os
import zlib
import json
import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from cachetools import LRUCache
from core.PathManager import PathManager
from core.UnifiedLoggingAgent import UnifiedLoggingAgent

logger = logging.getLogger(__name__)

class OptimizedMemoryManager:
    """
    Centralized memory management system with LRU caching and compression.
    Features:
    - Thread-safe operations
    - LRU caching for fast access
    - Data compression for reduced memory footprint
    - Automatic memory pruning
    - Segmented storage by context
    """

    def __init__(self, max_cache_size: int = 500):
        """
        Initialize the OptimizedMemoryManager.
        
        Args:
            max_cache_size: Maximum number of items to keep in the LRU cache
        """
        self.cache = LRUCache(maxsize=max_cache_size)
        self._lock = threading.Lock()
        self.logger = UnifiedLoggingAgent()
        
        # Memory segments for different types of data
        self.memory_segments = {
            "prompts": {},
            "feedback": {},
            "context": {},
            "system": {}
        }
        
        # Path setup
        self.memory_dir = PathManager.memory_dir
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # Load existing memory segments
        self._load_memory_segments()

    def set(self, key: str, data: Any, segment: str = "system") -> None:
        """
        Store data with compression in the specified memory segment.
        
        Args:
            key: Unique identifier for the data
            data: Data to store (will be JSON serialized)
            segment: Memory segment to store in
        """
        with self._lock:
            try:
                json_str = json.dumps(data)
                compressed = zlib.compress(json_str.encode('utf-8'))
                self.cache[f"{segment}:{key}"] = compressed
                self.memory_segments[segment][key] = compressed
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
        Retrieve data from cache or storage.
        
        Args:
            key: Unique identifier for the data
            segment: Memory segment to retrieve from
            
        Returns:
            Decompressed and deserialized data, or None if not found
        """
        cache_key = f"{segment}:{key}"
        try:
            # Try cache first
            if cache_key in self.cache:
                compressed = self.cache[cache_key]
            # Fall back to segment storage
            elif key in self.memory_segments[segment]:
                compressed = self.memory_segments[segment][key]
                # Update cache
                self.cache[cache_key] = compressed
            else:
                return None
            
            # Decompress and deserialize
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
        
        Args:
            key: Key to delete
            segment: Memory segment to delete from
            
        Returns:
            True if deletion was successful
        """
        with self._lock:
            try:
                cache_key = f"{segment}:{key}"
                if cache_key in self.cache:
                    del self.cache[cache_key]
                if key in self.memory_segments[segment]:
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
        """Clear an entire memory segment."""
        with self._lock:
            # Clear segment data
            self.memory_segments[segment].clear()
            
            # Clear related cache entries
            cache_keys = [k for k in self.cache.keys() if k.startswith(f"{segment}:")]
            for key in cache_keys:
                del self.cache[key]
            
            # Save empty segment
            self._save_segment(segment)

    def get_segment_keys(self, segment: str) -> List[str]:
        """Get all keys in a memory segment."""
        return list(self.memory_segments[segment].keys())

    def get_segment_size(self, segment: str) -> int:
        """Get the number of items in a memory segment."""
        return len(self.memory_segments[segment])

    def _load_memory_segments(self) -> None:
        """Load all memory segments from disk."""
        for segment in self.memory_segments:
            segment_file = os.path.join(self.memory_dir, f"{segment}_memory.json")
            if os.path.exists(segment_file):
                try:
                    with open(segment_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Convert stored base64 strings back to compressed bytes
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
        """Save a memory segment to disk."""
        segment_file = os.path.join(self.memory_dir, f"{segment}_memory.json")
        try:
            # Decompress all values for storage
            decompressed_data = {}
            for k, v in self.memory_segments[segment].items():
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
        """Get memory manager statistics."""
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
        Optimize memory usage by:
        1. Removing expired cache entries
        2. Recompressing data with optimal levels
        3. Consolidating fragmented storage
        """
        with self._lock:
            # Clear cache to remove any stale entries
            self.cache.clear()
            
            # Recompress all segments with optimal compression
            for segment, data in self.memory_segments.items():
                optimized_data = {}
                for key, compressed in data.items():
                    try:
                        # Decompress, then recompress with highest compression
                        json_str = zlib.decompress(compressed).decode('utf-8')
                        optimized_data[key] = zlib.compress(
                            json_str.encode('utf-8'),
                            level=9  # Highest compression level
                        )
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
