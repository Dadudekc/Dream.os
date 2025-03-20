import json
import os
import asyncio
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Optional, Dict, Any, Generator

# ✅ Correct imports for package structure (adjust as needed)
from core.PathManager import PathManager
from core.DiscordTemplateManager import DiscordTemplateManager

from jinja2 import Environment, FileSystemLoader, select_autoescape

class AIOutputLogAnalyzer:
    """
    Analyzes AI output logs stored in JSONL format.
    
    Features:
      - Community champion identification.
      - Community digest reporting.
      - Persistent context memory for adaptive AI responses.
      - Discord integration for reports and updates.
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
        self.log_dir = log_dir or PathManager.get_path('reinforcement_logs')
        self.verbose = verbose
        self.discord_manager = discord_manager

        # Load persistent memory
        self.context_memory = self.load_context_db()

        # Jinja2 Environment for template rendering
        self.env = Environment(
            loader=FileSystemLoader(PathManager.get_path('report_templates')),
            autoescape=select_autoescape(['html', 'xml', 'md'])
        )

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)

    # ------------------------------
    # CONTEXT DB MANAGEMENT
    # ------------------------------
    def load_context_db(self) -> Dict[str, Any]:
        if os.path.exists(self.CONTEXT_DB_PATH):
            with open(self.CONTEXT_DB_PATH, 'r', encoding='utf-8') as file:
                return json.load(file)
        return {
            "recent_responses": [],
            "user_profiles": {},
            "platform_memories": {},
            "trending_tags": []
        }

    def save_context_db(self) -> None:
        with open(self.CONTEXT_DB_PATH, 'w', encoding='utf-8') as file:
            json.dump(self.context_memory, file, indent=4)
        self._log(f"✅ Context DB saved at {self.CONTEXT_DB_PATH}")

    # ------------------------------
    # LOG ITERATION & VALIDATION
    # ------------------------------
    def iterate_logs(self) -> Generator[Dict[str, Any], None, None]:
        if not os.path.exists(self.log_dir):
            self._log(f"⚠️ Log directory not found: {self.log_dir}")
            return

        for filename in os.listdir(self.log_dir):
            if filename.endswith(".jsonl"):
                with open(os.path.join(self.log_dir, filename), "r", encoding="utf-8") as file:
                    for line in file:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line.strip())
                            validated = self._validate_log(entry)
                            if validated:
                                yield validated
                        except json.JSONDecodeError as e:
                            self._log(f"❌ JSON decode error in {filename}: {e}")

    def _validate_log(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(entry, dict):
            return None
        timestamp = entry.get("timestamp")
        if not timestamp or not self._parse_date(timestamp):
            self._log("❌ Invalid or missing timestamp.")
            return None
        result = entry.get("result", "").lower()
        result = result if result in self.VALID_RESULTS else "unknown"

        return {
            "timestamp": timestamp,
            "result": result,
            "tags": entry.get("tags", []),
            "ai_output": entry.get("ai_output", ""),
            "user": entry.get("user", "unknown"),
            "platform": entry.get("platform", "general")
        }

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            return None

    # ------------------------------
    # CONTEXT EXTRACTION
    # ------------------------------
    def extract_context_from_logs(self, max_entries: int = 50):
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
                "text": ai_output, "tags": tags, "user": user, "timestamp": timestamp
            })
            user_context[user].append({
                "text": ai_output, "tags": tags, "timestamp": timestamp
            })
            platform_memories[platform].append(ai_output)
            tag_counter.update(tags)

        self.context_memory["recent_responses"] = sorted(extracted_responses, key=lambda x: x["timestamp"])[-max_entries:]
        self.context_memory["user_profiles"] = {
            user: {"last_interactions": sorted(entries, key=lambda x: x["timestamp"])[-10:]}
            for user, entries in user_context.items()
        }
        self.context_memory["platform_memories"] = {
            platform: responses[-max_entries:] for platform, responses in platform_memories.items()
        }
        self.context_memory["trending_tags"] = tag_counter.most_common(10)

        self.save_context_db()
        self._log("✅ Context extracted and saved.")

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

    def export_summary_report(self, output_file: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
        summary = self.summarize(start_date, end_date)
        template = self.env.get_template("ai_summary_report.md.j2")
        report_content = template.render(summary=summary, generated_on=datetime.now().isoformat())

        output_path = os.path.join(PathManager.get_path('reinforcement_logs'), output_file)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        self._log(f"✅ Report exported to {output_path}")
        return report_content

    async def send_discord_report(self, start_date: Optional[str] = None, end_date: Optional[str] = None):
        if not self.discord_manager:
            self._log("❌ Discord manager not initialized.")
            return

        summary = self.summarize(start_date, end_date)
        message = self.discord_manager.render_message("ai_summary_discord", summary)
        await self.discord_manager.send_message(message)

        self._log("📤 Discord summary sent.")

    def send_discord_report_sync(self, start_date: Optional[str] = None, end_date: Optional[str] = None):
        asyncio.run(self.send_discord_report(start_date, end_date))
