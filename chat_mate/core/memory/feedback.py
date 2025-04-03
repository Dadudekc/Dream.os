"""
Unified Feedback Memory

This module provides the UnifiedFeedbackMemory class that handles feedback storage,
retrieval, and analysis across the system.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class FeedbackEntry:
    """
    Represents a single feedback entry with metadata.
    """
    def __init__(self, content: str, source: str, timestamp: Optional[datetime] = None):
        self.content = content
        self.source = source
        self.timestamp = timestamp or datetime.now()
        self.processed = False
        self.tags: List[str] = []
        self.metadata: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary for storage."""
        return {
            "content": self.content,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "processed": self.processed,
            "tags": self.tags,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeedbackEntry':
        """Create entry from dictionary."""
        entry = cls(
            content=data["content"],
            source=data["source"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )
        entry.processed = data.get("processed", False)
        entry.tags = data.get("tags", [])
        entry.metadata = data.get("metadata", {})
        return entry

class UnifiedFeedbackMemory:
    """
    Singleton class that provides global access to the UnifiedFeedbackMemory.
    Handles storage, retrieval, and analysis of system feedback across components.
    """
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UnifiedFeedbackMemory, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not UnifiedFeedbackMemory._initialized:
            self.logger = logging.getLogger(__name__)
            self.feedback_file = Path("memory/unified_feedback.json")
            self.entries: List[FeedbackEntry] = []
            self._load_feedback()
            UnifiedFeedbackMemory._initialized = True

    def _load_feedback(self):
        """Load feedback from file."""
        try:
            if self.feedback_file.exists():
                with open(self.feedback_file, 'r') as f:
                    data = json.load(f)
                    self.entries = [FeedbackEntry.from_dict(entry) for entry in data]
            else:
                self.entries = []
                self._save_feedback()  # Create initial file
        except Exception as e:
            self.logger.error(f"Failed to load feedback: {e}")
            self.entries = []

    def _save_feedback(self):
        """Save feedback to file."""
        try:
            self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.feedback_file, 'w') as f:
                json.dump([entry.to_dict() for entry in self.entries], f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save feedback: {e}")

    def add_feedback(self, content: str, source: str, tags: Optional[List[str]] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> FeedbackEntry:
        """
        Add new feedback entry.
        
        Args:
            content: The feedback content.
            source: Source of the feedback (e.g., "user", "system", "agent").
            tags: Optional list of tags for categorization.
            metadata: Optional metadata dictionary.
            
        Returns:
            The created FeedbackEntry.
        """
        entry = FeedbackEntry(content, source)
        if tags:
            entry.tags = tags
        if metadata:
            entry.metadata = metadata
        self.entries.append(entry)
        self._save_feedback()
        return entry

    def get_feedback(self, source: Optional[str] = None, 
                    tags: Optional[List[str]] = None,
                    processed: Optional[bool] = None) -> List[FeedbackEntry]:
        """
        Get feedback entries matching criteria.
        
        Args:
            source: Optional source to filter by.
            tags: Optional list of tags to filter by.
            processed: Optional processing status to filter by.
            
        Returns:
            List of matching FeedbackEntry objects.
        """
        results = self.entries

        if source:
            results = [e for e in results if e.source == source]
        if tags:
            results = [e for e in results if all(tag in e.tags for tag in tags)]
        if processed is not None:
            results = [e for e in results if e.processed == processed]

        return results

    def mark_processed(self, entry: FeedbackEntry):
        """Mark a feedback entry as processed."""
        entry.processed = True
        self._save_feedback()

    def add_tags(self, entry: FeedbackEntry, tags: List[str]):
        """Add tags to a feedback entry."""
        entry.tags.extend([tag for tag in tags if tag not in entry.tags])
        self._save_feedback()

    def update_metadata(self, entry: FeedbackEntry, metadata: Dict[str, Any]):
        """Update metadata for a feedback entry."""
        entry.metadata.update(metadata)
        self._save_feedback()

    def clear_all(self):
        """Clear all feedback entries."""
        self.entries = []
        self._save_feedback()

    def get_stats(self) -> Dict[str, Any]:
        """Get feedback statistics."""
        return {
            "total_entries": len(self.entries),
            "processed_entries": len([e for e in self.entries if e.processed]),
            "sources": {source: len([e for e in self.entries if e.source == source])
                       for source in set(e.source for e in self.entries)},
            "tags": {tag: len([e for e in self.entries if tag in e.tags])
                    for tag in set(tag for e in self.entries for tag in e.tags)}
        } 