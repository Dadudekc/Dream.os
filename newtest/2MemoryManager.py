import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from jinja2 import Environment, FileSystemLoader

# -----------------------------
# Database Manager for long-term storage
# -----------------------------
class DatabaseManager:
    def __init__(self, db_file: str = "memory/engagement_memory.db"):
        self.db_file = db_file
        self.conn = sqlite3.connect(self.db_file)
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
        timestamp = datetime.now(timezone.utc).isoformat() + "Z"
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
        # Map rows to dicts
        columns = ["platform", "username", "interaction_id", "timestamp", "response", "sentiment", "success", "chatgpt_url"]
        return [dict(zip(columns, row)) for row in rows]

    def close(self):
        self.conn.close()


# -----------------------------
# Memory Manager (JSON, DB & Jinja)
# -----------------------------
class MemoryManager:
    """
    Enhanced memory manager that:
      - Uses JSON for short-term memory storage.
      - Stores interactions in a SQLite DB for long-term retention.
      - Uses Jinja templates to render narrative outputs.
    """

    def __init__(self, memory_file: str = "memory/engagement_memory.json", db_file: str = "memory/engagement_memory.db", template_dir: str = "templates"):
        self.memory_file = memory_file
        self.data = {}
        self._load_memory()
        self.db_manager = DatabaseManager(db_file)
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        self._ensure_integrity()

    # ----------------------------------------
    # JSON Memory Operations
    # ----------------------------------------
    def _load_memory(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}
        else:
            self.data = {}
        self._ensure_integrity()

    def _save_memory(self):
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)

    def _ensure_integrity(self):
        self.data.setdefault("platforms", {})
        self.data.setdefault("conversations", {})

    # ----------------------------------------
    # Interaction Recording (Enhanced)
    # ----------------------------------------
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
        timestamp = datetime.now(timezone.utc).isoformat() + "Z"
        record = {
            "platform": platform,
            "username": username,
            "interaction_id": interaction_id,
            "timestamp": timestamp,
            "response": response,
            "sentiment": sentiment,
            "success": success,
            "chatgpt_url": chatgpt_url
        }

        # Record in JSON (short-term memory)
        platform_data = self.data["platforms"].setdefault(platform, {})
        user_data = platform_data.setdefault(username, [])
        user_data.append(record)

        if interaction_id:
            conv = self.data["conversations"].setdefault(interaction_id, [])
            conv.append(record)

        self._save_memory()

        # Record in DB (long-term storage)
        self.db_manager.record_interaction(record)

    # ----------------------------------------
    # Conversation Lifecycle Management (NEW)
    # ----------------------------------------
    def initialize_conversation(self, interaction_id: str, metadata: Dict[str, Any]):
        if interaction_id not in self.data["conversations"]:
            self.data["conversations"][interaction_id] = []
            self.data["conversations"][interaction_id + "_metadata"] = {
                "initialized_at": datetime.now(timezone.utc).isoformat() + "Z",
                "metadata": metadata
            }
            self._save_memory()
        # Also store in DB
        self.db_manager.initialize_conversation(interaction_id, metadata)

    def retrieve_conversation(self, interaction_id: str) -> List[Dict[str, Any]]:
        # Prefer DB retrieval for long-term data
        return self.db_manager.get_conversation(interaction_id)

    def export_conversation_for_finetuning(self, interaction_id: str, export_path: str) -> bool:
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
        with open(export_path, 'w', encoding='utf-8') as f:
            for entry in fine_tuning_data:
                f.write(json.dumps(entry) + "\n")
        
        return True

    # ----------------------------------------
    # User History Retrieval
    # ----------------------------------------
    def get_user_history(self, platform: str, username: str, limit: int = 5) -> List[Dict[str, Any]]:
        user_history = self.data.get("platforms", {}).get(platform, {}).get(username, [])
        return user_history[-limit:]

    # ----------------------------------------
    # Analytics & Insights
    # ----------------------------------------
    def user_sentiment_summary(self, platform: str, username: str) -> Dict[str, Any]:
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
        platform_users = self.data.get("platforms", {}).get(platform, {})
        if username in platform_users:
            del platform_users[username]
            self._save_memory()

    def clear_platform_history(self, platform: str):
        if platform in self.data["platforms"]:
            del self.data["platforms"][platform]
            self._save_memory()

    # ----------------------------------------
    # Narrative Generation using Jinja
    # ----------------------------------------
    def generate_narrative(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Generate a narrative using a Jinja template.
        Example template might be 'dreamscape_template.txt' in the templates directory.
        """
        template = self.jinja_env.get_template(template_name)
        narrative = template.render(**context)
        return narrative

    # ----------------------------------------
    # Close resources
    # ----------------------------------------
    def close(self):
        self.db_manager.close()


# -----------------------------
# Example Usage
# -----------------------------
if __name__ == "__main__":
    # Create an instance of the memory manager
    mm = MemoryManager()

    # Record an interaction
    mm.record_interaction(
        platform="Discord",
        username="Victor",
        response="System audit complete. All systems are online.",
        sentiment="positive",
        success=True,
        interaction_id="audit_001",
        chatgpt_url="http://chat.openai.com/audit_001"
    )

    # Initialize a conversation with metadata
    mm.initialize_conversation("audit_001", {"topic": "System Audit", "priority": "High"})

    # Generate a narrative using a Jinja template.
    # Make sure you have a template file (e.g., templates/dreamscape_template.txt) set up.
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
    print(narrative)

    # Close resources when done.
    mm.close()