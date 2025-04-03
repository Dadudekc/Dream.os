"""Module containing chat message related classes."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any, Dict


@dataclass
class ChatMessage:
    """Represents a chat message with metadata."""
    content: str
    timestamp: datetime
    sender: str
    message_type: str = "text"
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary."""
        return {
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "sender": self.sender,
            "message_type": self.message_type,
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        """Create a ChatMessage from a dictionary."""
        return cls(
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            sender=data["sender"],
            message_type=data.get("message_type", "text"),
            metadata=data.get("metadata", {})
        )


class MessageEncoder(json.JSONEncoder):
    """JSON encoder for ChatMessage objects."""
    def default(self, obj):
        if isinstance(obj, ChatMessage):
            return obj.to_dict()
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj) 