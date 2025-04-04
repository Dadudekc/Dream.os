"""
Database Manager for Long-Term Storage

This module provides the DatabaseManager class that handles SQLite-based storage
of interactions and conversation metadata with WAL mode support.
"""

import json
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

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
        """Initialize database tables if they don't exist."""
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
        
        Args:
            record: Dictionary containing interaction data with fields matching
                   the interactions table schema.
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
        
        Args:
            interaction_id: Unique identifier for the conversation.
            metadata: Dictionary of metadata to store.
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
        
        Args:
            interaction_id: The conversation ID to retrieve.
            
        Returns:
            List of interaction records as dictionaries.
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

    def get_user_interactions(self, platform: str, username: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get recent interactions for a specific user on a platform.
        
        Args:
            platform: The platform name.
            username: The username to query.
            limit: Optional limit on number of records to return.
            
        Returns:
            List of interaction records as dictionaries.
        """
        c = self.conn.cursor()
        query = """
            SELECT 
                platform, username, interaction_id, timestamp, response, sentiment, success, chatgpt_url
            FROM interactions
            WHERE platform = ? AND username = ?
            ORDER BY timestamp DESC
        """
        if limit:
            query += f" LIMIT {int(limit)}"
            
        c.execute(query, (platform, username))
        rows = c.fetchall()
        columns = ["platform", "username", "interaction_id", "timestamp", "response", "sentiment", "success", "chatgpt_url"]
        return [dict(zip(columns, row)) for row in rows]

    def get_conversation_metadata(self, interaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific conversation.
        
        Args:
            interaction_id: The conversation ID to query.
            
        Returns:
            Dictionary of metadata if found, None otherwise.
        """
        c = self.conn.cursor()
        c.execute("""
            SELECT metadata, initialized_at
            FROM conversations_metadata
            WHERE interaction_id = ?
        """, (interaction_id,))
        row = c.fetchone()
        if row:
            metadata = json.loads(row[0])
            metadata["initialized_at"] = row[1]
            return metadata
        return None

    def clear_user_interactions(self, platform: str, username: str):
        """
        Delete all interactions for a specific user on a platform.
        
        Args:
            platform: The platform name.
            username: The username whose interactions should be deleted.
        """
        c = self.conn.cursor()
        c.execute("""
            DELETE FROM interactions
            WHERE platform = ? AND username = ?
        """, (platform, username))
        self.conn.commit()

    def close(self):
        """Close the database connection."""
        self.conn.close() 