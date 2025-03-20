import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

class MemoryManager:
    """
    Enhanced memory manager supporting structured conversation cataloging,
    contextual fine-tuning integration, and conversation lifecycle management.
    """

    def __init__(self, memory_file: str = "memory/engagement_memory.json"):
        self.memory_file = memory_file
        self.data = {}
        self._load_memory()

    # ----------------------------------------
    # Memory Operations
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
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Platform-user level recording
        platform_data = self.data["platforms"].setdefault(platform, {})
        user_data = platform_data.setdefault(username, [])
        interaction_record = {
            "interaction_id": interaction_id,
            "timestamp": timestamp,
            "response": response,
            "sentiment": sentiment,
            "success": success,
            "chatgpt_url": chatgpt_url
        }
        user_data.append(interaction_record)

        # Conversation-level indexing
        if interaction_id:
            conversation_data = self.data["conversations"].setdefault(interaction_id, [])
            conversation_data.append(interaction_record)

        self._save_memory()

    # ----------------------------------------
    # Conversation Lifecycle Management (NEW)
    # ----------------------------------------

    def initialize_conversation(self, interaction_id: str, metadata: Dict[str, Any]):
        if interaction_id not in self.data["conversations"]:
            self.data["conversations"][interaction_id] = []
            self.data["conversations"][interaction_id+"_metadata"] = {
                "initialized_at": datetime.utcnow().isoformat() + "Z",
                "metadata": metadata
            }
            self._save_memory()

    def retrieve_conversation(self, interaction_id: str) -> List[Dict[str, Any]]:
        return self.data["conversations"].get(interaction_id, [])

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
    # User History Retrieval (Updated)
    # ----------------------------------------

    def get_user_history(
        self,
        platform: str,
        username: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        user_history = self.data.get("platforms", {}).get(platform, {}).get(username, [])
        return user_history[-limit:]

    # ----------------------------------------
    # Analytics & Insights (Unchanged)
    # ----------------------------------------

    def user_sentiment_summary(
        self,
        platform: str,
        username: str
    ) -> Dict[str, Any]:
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
