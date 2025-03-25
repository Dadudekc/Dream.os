import json
import os
import asyncio
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Optional, Dict, Any, Generator

# ✅ Correct imports for package structure (adjust as needed)
from utils.path_manager import PathManager
from core.DiscordTemplateManager import DiscordTemplateManager
from core.FileManager import FileManager
from core.UnifiedLoggingAgent import UnifiedLoggingAgent

from jinja2 import Environment, FileSystemLoader, select_autoescape

class AIOutputLogAnalyzer:
    """
    Analyzes AI output logs stored in JSONL format.
    Now integrated with UnifiedLoggingAgent for consistent log access.
    
    Features:
      - Community champion identification
      - Community digest reporting
      - Persistent context memory for adaptive AI responses
      - Discord integration for reports and updates
    """

    VALID_RESULTS = {"successful", "partial", "failed"}

    # Static path assignment for context DB
    CONTEXT_DB_PATH = PathManager.get_path('context_db')  # Use PathManager registry
    
    def __init__(
        self,
        log_dir: Optional[str] = None,
        verbose: bool = True,
        discord_manager: Optional[DiscordTemplateManager] = None
    ):
        self.verbose = verbose
        self.discord_manager = discord_manager

        # Initialize unified logging
        self.unified_logger = UnifiedLoggingAgent()
        
        # Initialize file management
        self.file_manager = FileManager()
        
        # Load persistent memory
        self.context_memory = self.load_context_db()

        # Jinja2 Environment for template rendering
        self.env = Environment(
            loader=FileSystemLoader(PathManager.get_path('report_templates')),
            autoescape=select_autoescape(['html', 'xml', 'md'])
        )

    def _log(self, message: str, level: str = "info") -> None:
        """Internal logging using UnifiedLoggingAgent."""
        if self.verbose:
            self.unified_logger.log_system_event(
                event_type="analyzer",
                message=message,
                level=level
            )

    # ------------------------------
    # CONTEXT DB MANAGEMENT
    # ------------------------------
    def load_context_db(self) -> Dict[str, Any]:
        """Load context database using FileManager."""
        data = self.file_manager.load_file(
            PathManager.get_path('context_db'),
            file_type="json"
        )
        if not data:
            data = {
                "recent_responses": [],
                "user_profiles": {},
                "platform_memories": {},
                "trending_tags": []
            }
        return data

    def save_context_db(self) -> None:
        """Save context database using FileManager."""
        self.file_manager.save_memory_state(
            content=self.context_memory,
            memory_type="context"
        )
        self._log("Context DB saved successfully")

    # ------------------------------
    # LOG ITERATION & VALIDATION
    # ------------------------------
    def iterate_logs(self) -> Generator[Dict[str, Any], None, None]:
        """
        Iterate through AI output logs using UnifiedLoggingAgent.
        """
        logs = self.unified_logger.get_logs(
            domain="ai_output",
            filters={"result": {"$in": list(self.VALID_RESULTS)}}
        )
        
        for entry in logs:
            validated = self._validate_log(entry)
            if validated:
                yield validated

    def _validate_log(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate a log entry."""
        if not isinstance(entry, dict):
            return None
            
        metadata = entry.get("metadata", {})
        result = metadata.get("result", "").lower()
        result = result if result in self.VALID_RESULTS else "unknown"

        return {
            "timestamp": entry["timestamp"],
            "result": result,
            "tags": entry.get("tags", []),
            "ai_output": entry["message"],
            "user": metadata.get("user", "unknown"),
            "platform": metadata.get("platform", "general")
        }

    # ------------------------------
    # CONTEXT EXTRACTION
    # ------------------------------
    def extract_context_from_logs(self, max_entries: int = 50) -> None:
        """Extract context from logs using UnifiedLoggingAgent."""
        extracted_responses = []
        user_context = defaultdict(list)
        tag_counter = Counter()
        platform_memories = defaultdict(list)

        for entry in self.iterate_logs():
            if entry["result"] != "successful":
                continue

            ai_output = entry["ai_output"].strip()
            if not ai_output:
                continue

            user = entry["user"]
            tags = entry["tags"]
            platform = entry["platform"]
            timestamp = entry["timestamp"]

            extracted_responses.append({
                "text": ai_output,
                "tags": tags,
                "user": user,
                "timestamp": timestamp
            })
            
            user_context[user].append({
                "text": ai_output,
                "tags": tags,
                "timestamp": timestamp
            })
            
            platform_memories[platform].append(ai_output)
            tag_counter.update(tags)

        self.context_memory["recent_responses"] = sorted(
            extracted_responses,
            key=lambda x: x["timestamp"]
        )[-max_entries:]
        
        self.context_memory["user_profiles"] = {
            user: {
                "last_interactions": sorted(
                    entries,
                    key=lambda x: x["timestamp"]
                )[-10:]
            }
            for user, entries in user_context.items()
        }
        
        self.context_memory["platform_memories"] = {
            platform: responses[-max_entries:]
            for platform, responses in platform_memories.items()
        }
        
        self.context_memory["trending_tags"] = tag_counter.most_common(10)

        self.save_context_db()
        self._log("Context extracted and saved")

    # ------------------------------
    # CONTEXT RETRIEVAL
    # ------------------------------
    def get_recent_context(self, limit: int = 5) -> str:
        return "\n".join([
            f"- {resp['text'][:200]}..." for resp in self.context_memory.get("recent_responses", [])[-limit:]
        ])

    def get_user_context(self, user: str) -> str:
        profile = self.context_memory.get("user_profiles", {}).get(user, {})
        return "\n".join([
            f"- {interaction['text'][:200]}..." for interaction in profile.get("last_interactions", [])
        ])

    def get_platform_context(self, platform: str, limit: int = 5) -> str:
        memories = self.context_memory.get("platform_memories", {}).get(platform, [])
        return "\n".join([
            f"- {text[:200]}..." for text in memories[-limit:]
        ])

    # ------------------------------
    # COMMUNITY ENGAGEMENT
    # ------------------------------
    def identify_community_champions(self) -> List[str]:
        champions = list(self.summarize().get("top_users", {}).keys())
        self._log(f"🏆 Top Community Champions: {champions}")
        return champions

    def trigger_community_invites(self, ai_agent, personalized: bool = True) -> Dict[str, str]:
        champions = self.identify_community_champions()
        invites = {}

        for user in champions:
            context = self.get_user_context(user)
            prompt = f"""
You are Victor. Craft a { "personalized" if personalized else "general" } invite for {user} to join my exclusive community of system builders and traders.
Highlight: {context if personalized else "our collective mission of convergence and growth"}.
Tone: visionary, authentic, strategic.
"""
            invite_message = ai_agent.ask(prompt=prompt, metadata={"platform": "Community", "user": user})
            invites[user] = invite_message
            self._log(f"✅ Invite for {user}: {invite_message[:80]}...")

        return invites

    # ------------------------------
    # SUMMARY & REPORTING
    # ------------------------------
    def summarize(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        summary = {
            "total_entries": 0,
            "successful": 0,
            "partial": 0,
            "failed": 0,
            "unknown": 0,
            "avg_response_length": 0.0,
            "tag_distribution": Counter(),
            "top_users": Counter(),
            "date_range": f"{start_date or 'beginning'} to {end_date or 'end'}"
        }

        start_dt = self._parse_date(start_date) if start_date else None
        end_dt = self._parse_date(end_date) if end_date else None
        total_length = 0

        for entry in self.iterate_logs():
            entry_dt = self._parse_date(entry["timestamp"])
            if start_dt and entry_dt < start_dt:
                continue
            if end_dt and entry_dt > end_dt:
                continue

            summary[entry["result"]] += 1
            summary["total_entries"] += 1
            summary["tag_distribution"].update(entry["tags"])
            summary["top_users"].update([entry["user"]])
            total_length += len(entry["ai_output"])

        if summary["total_entries"]:
            summary["avg_response_length"] = round(total_length / summary["total_entries"], 2)

        summary["top_users"] = dict(summary["top_users"].most_common(5))
        return summary

    def export_summary_report(self, report_data: Dict[str, Any]) -> Optional[str]:
        """Export a summary report using UnifiedLoggingAgent."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Log the report data
        filepath = self.unified_logger.log(
            message=json.dumps(report_data, indent=2),
            domain="audit",
            metadata={"report_type": "summary"},
            tags=["analysis", "summary"]
        )
        
        if filepath:
            self._log(f"Summary report exported to {filepath}")
        else:
            self._log("Failed to export summary report", level="error")
            
        return filepath

    async def send_discord_report(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> None:
        """Send a Discord report using UnifiedLoggingAgent for tracking."""
        if not self.discord_manager:
            self._log("Discord manager not initialized", level="warning")
            return

        summary = self.summarize(start_date, end_date)
        message = self.discord_manager.render_message("ai_summary_discord", summary)
        
        try:
            await self.discord_manager.send_message(message)
            self.unified_logger.log_social(
                platform="discord",
                event_type="report",
                content="AI Summary Report sent successfully",
                metadata={"summary_data": summary}
            )
        except Exception as e:
            self._log(f"Failed to send Discord report: {e}", level="error")

    def send_discord_report_sync(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> None:
        """Synchronous wrapper for send_discord_report."""
        asyncio.run(self.send_discord_report(start_date, end_date))

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            return None
