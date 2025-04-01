"""
Core Memory Management Module

This module provides a unified interface for memory management across the application,
including short-term caching, long-term storage, and specialized memory managers for
different contexts.
"""

from .manager import MemoryManager
from .database import DatabaseManager
from .context import ContextMemoryManager
from .feedback import UnifiedFeedbackMemory
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class FeedbackEntry:
    """Data class for feedback entries."""
    
    id: str
    type: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata or {}
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeedbackEntry':
        """Create from dictionary."""
        return cls(
            id=data["id"],
            type=data["type"],
            content=data["content"],
            metadata=data.get("metadata", {})
        )

__all__ = [
    'MemoryManager',
    'DatabaseManager',
    'ContextMemoryManager',
    'UnifiedFeedbackMemory',
    'FeedbackEntry'
] 