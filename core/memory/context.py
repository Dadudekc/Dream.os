"""
Context Memory Manager

This module provides the ContextMemoryManager class that handles context-specific
memory management, particularly for Dreamscape episode generation and other
context-dependent features.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

class ContextMemoryManager:
    """
    Manages context-specific memory storage and retrieval, particularly for
    Dreamscape episode generation and other context-dependent features.
    """

    def __init__(self, output_dir: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the ContextMemoryManager.

        Args:
            output_dir: Directory for storing context files.
            logger: Optional logger instance.
        """
        self.output_dir = Path(output_dir)
        self.logger = logger or logging.getLogger(__name__)
        self.context_data: Dict[str, Any] = {}
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        """Ensure the output directory exists."""
        os.makedirs(self.output_dir, exist_ok=True)

    def save_context(self, context_id: str, data: Dict[str, Any]):
        """
        Save context data to file.

        Args:
            context_id: Unique identifier for the context.
            data: Context data to save.
        """
        try:
            file_path = self.output_dir / f"{context_id}_context.json"
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            self.context_data[context_id] = data
            self.logger.info(f"Saved context {context_id} to {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save context {context_id}: {e}")
            raise

    def load_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """
        Load context data from file.

        Args:
            context_id: Unique identifier for the context.

        Returns:
            Context data if found, None otherwise.
        """
        try:
            file_path = self.output_dir / f"{context_id}_context.json"
            if file_path.exists():
                with open(file_path, 'r') as f:
                    data = json.load(f)
                self.context_data[context_id] = data
                return data
            return None
        except Exception as e:
            self.logger.error(f"Failed to load context {context_id}: {e}")
            return None

    def update_context(self, context_id: str, updates: Dict[str, Any], create_if_missing: bool = True) -> bool:
        """
        Update existing context with new data.

        Args:
            context_id: Unique identifier for the context.
            updates: Dictionary of updates to apply.
            create_if_missing: If True, create context if it doesn't exist.

        Returns:
            True if successful, False otherwise.
        """
        try:
            current = self.load_context(context_id)
            if current is None:
                if create_if_missing:
                    current = {}
                else:
                    return False

            # Deep update the context
            self._deep_update(current, updates)
            self.save_context(context_id, current)
            return True
        except Exception as e:
            self.logger.error(f"Failed to update context {context_id}: {e}")
            return False

    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]):
        """
        Recursively update a dictionary.

        Args:
            target: Dictionary to update.
            source: Dictionary containing updates.
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value

    def delete_context(self, context_id: str) -> bool:
        """
        Delete context data and file.

        Args:
            context_id: Unique identifier for the context.

        Returns:
            True if successful, False otherwise.
        """
        try:
            file_path = self.output_dir / f"{context_id}_context.json"
            if file_path.exists():
                os.remove(file_path)
            if context_id in self.context_data:
                del self.context_data[context_id]
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete context {context_id}: {e}")
            return False

    def list_contexts(self) -> Dict[str, Dict[str, Any]]:
        """
        List all available contexts and their data.

        Returns:
            Dictionary mapping context IDs to their data.
        """
        contexts = {}
        try:
            for file_path in self.output_dir.glob("*_context.json"):
                context_id = file_path.stem.replace("_context", "")
                data = self.load_context(context_id)
                if data:
                    contexts[context_id] = data
        except Exception as e:
            self.logger.error(f"Failed to list contexts: {e}")
        return contexts

    def clear_all(self):
        """Clear all context data and files."""
        try:
            for file_path in self.output_dir.glob("*_context.json"):
                os.remove(file_path)
            self.context_data.clear()
            self.logger.info("Cleared all context data")
        except Exception as e:
            self.logger.error(f"Failed to clear all contexts: {e}")
            raise 