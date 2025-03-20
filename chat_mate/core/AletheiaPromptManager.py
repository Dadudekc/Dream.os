import os
import sys
import json
import re
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Union, Callable
from jinja2 import Environment, FileSystemLoader

# Setup Logging First
logger = logging.getLogger("Aletheia_PromptManager")
logging.basicConfig(level=logging.INFO)

# Determine the project root directory (d:/overnight_scripts/chat_mate)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Set the template path assuming your templates folder is directly under the project root.
template_path = os.path.join(ROOT_DIR, "templates", "prompt_templates")

logger.info(f"ROOT_DIR is set to: {ROOT_DIR}")
logger.info(f"Jinja2 template path is set to: {template_path}")

# Optionally log files in the directory to confirm presence
try:
    logger.info(f"Templates found: {os.listdir(template_path)}")
except Exception as e:
    logger.warning(f"Could not list templates in {template_path}: {e}")

# Add ROOT_DIR to sys.path if it isn't already
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Import DiscordManager from your core directory
from core.DiscordManager import DiscordManager


class AletheiaPromptManager:
    """
    Aletheia - Autonomous Architect of Strategic Convergence.

    This class handles:
      - Persistent prompt storage & retrieval.
      - Adaptive structured memory updates.
      - FULL SYNC integration with Victor.OS.
      - Auto-dispatch of Discord notifications on episode archiving.
    Managed by Aletheia (Thea).
    """

    def __init__(self, prompt_file: str = 'chat_mate/prompts.json', memory_file: str = 'memory/persistent_memory.json'):
        self.prompt_file: str = prompt_file
        self.memory_file: str = memory_file

        self.prompts: Dict[str, dict] = {}
        self.default_prompts: Dict[str, dict] = self._get_default_prompts()

        # Initialize persistent memory state with versioning and a structured data container.
        self.memory_state: Dict[str, Any] = {
            "version": 1,
            "last_updated": None,
            "data": {}  # Domain-specific data goes here.
        }
        self._lock = threading.Lock()

        # Initialize Jinja2 Environment to load external templates from the absolute path.
        # FIX: Removed the incorrect "chat_mate" directory from the path
        self.jinja_env = Environment(loader=FileSystemLoader(template_path))

        # Initialize DiscordManager for notifications.
        self.discord_manager = DiscordManager()

        logger.info(f"🚀 Aletheia initializing with prompt file: {self.prompt_file} and memory file: {self.memory_file}")

        self.load_prompts()
        self.load_memory_state()

    def _get_default_prompts(self) -> Dict[str, dict]:
        """
        Define default prompts for the system.
        These serve as a fallback if no external prompt file is found.
        """
        return {
            "devlog": {
                "prompt": (
                    "You are Aletheia, Victor’s autonomous architect of convergence, running in FULL SYNC mode. "
                    "Current memory state is as follows: {{ CURRENT_MEMORY_STATE }}\n\n"
                    "Generate a devlog entry written in Victor’s natural tone—raw, introspective, conversational. "
                    "Structure clearly: 1) What was worked on 2) What broke or was tricky 3) What’s next. "
                    "Use natural pauses ('...') and end with a motivational insight.\n\n"
                    "After the narrative, output a separate block labeled MEMORY_UPDATE in JSON format including:\n"
                    "- project_milestones,\n"
                    "- system_optimizations,\n"
                    "- quests_completed,\n"
                    "- feedback_loops_triggered,\n"
                    "- breakthroughs_or_strategy_evolutions.\n\n"
                    "Respond with the narrative first, then the MEMORY_UPDATE block."
                ),
                "model": "gpt-4o-mini"
            },
            "dreamscape": {
                "prompt": (
                    "You are The Architect’s Edge, Aletheia, operating in FULL SYNC. "
                    "Current memory state is as follows: {{ CURRENT_MEMORY_STATE }}\n\n"
                    "Chronicle Victor’s work as an evolving MMORPG saga called The Dreamscape. "
                    "Describe his actions as quests, domain raids, anomaly hunts, and PvP conflicts. "
                    "Convert protocols, workflows, and tools into legendary artifacts. "
                    "End with a visionary call to action.\n\n"
                    "After the narrative, output a separate MEMORY_UPDATE block in JSON format including:\n"
                    "- skill_level_advancements,\n"
                    "- newly_stabilized_domains,\n"
                    "- newly_unlocked_protocols,\n"
                    "- quest_completions,\n"
                    "- architect_tier_progression.\n\n"
                    "Respond with only the narrative and MEMORY_UPDATE block."
                ),
                "model": "gpt-4o-mini",
                "episode_counter": 1
            },
            "content_ideas": {
                "prompt": (
                    "You are Aletheia, the autonomous architect of Victor’s content strategy engine, running in FULL SYNC mode. "
                    "Current memory state is as follows: {{ CURRENT_MEMORY_STATE }}\n\n"
                    "Analyze this conversation and extract high-leverage content opportunities for momentum, expansion, and convergence. "
                    "Provide actionable insights and scalable ideas for devlogs, tutorials, or campaigns.\n\n"
                    "After the analysis, output a separate MEMORY_UPDATE block in JSON format including:\n"
                    "- content_ideas_logged,\n"
                    "- platforms_targeted,\n"
                    "- content_loops_triggered.\n\n"
                    "Respond with only the content strategy and MEMORY_UPDATE block."
                ),
                "model": "gpt-4o-mini"
            }
        }

    def load_prompts(self) -> None:
        """
        Load prompts from a JSON file; fallback to default if needed.
        """
        with self._lock:
            if os.path.exists(self.prompt_file):
                try:
                    with open(self.prompt_file, 'r', encoding='utf-8') as file:
                        self.prompts = json.load(file)
                    logger.info(f"✅ Loaded prompts from {self.prompt_file}")
                except Exception as e:
                    logger.error(f"❌ Error loading prompts: {e}")
                    self._fallback_to_defaults()
            else:
                logger.warning("⚠️ Prompt file not found. Loading default prompts.")
                self._fallback_to_defaults()

    def save_prompts(self) -> None:
        """
        Asynchronously save prompts to a file.
        """
        self._async_save(self.prompt_file, self.prompts, "prompts")

    def _fallback_to_defaults(self) -> None:
        """
        Reset to default prompts and save.
        """
        self.prompts = self._get_default_prompts().copy()
        logger.info("🔄 Loaded default prompts.")
        self.save_prompts()

    def _async_save(self, file_path: str, data: Any, data_type: str) -> None:
        """
        Asynchronously save provided data to a file.
        """
        def save_task() -> None:
            with self._lock:
                try:
                    with open(file_path, 'w', encoding='utf-8') as file:
                        json.dump(data, file, indent=4, ensure_ascii=False)
                    logger.info(f"💾 {data_type.capitalize()} saved to {file_path}")
                except Exception as e:
                    logger.error(f"❌ Failed to save {data_type}: {e}")
        threading.Thread(target=save_task, daemon=True).start()

    def get_prompt(self, prompt_type: str) -> str:
        """
        Retrieve and render the prompt for a given type using an external Jinja template.
        """
        entry = self.prompts.get(prompt_type)
        if not entry or "prompt" not in entry:
            raise ValueError(f"Prompt type '{prompt_type}' is not defined.")

        try:
            # Since the loader already points to 'prompt_templates', we only need the filename.
            template = self.jinja_env.get_template(f"{prompt_type}.j2")
        except Exception as e:
            logger.error(f"❌ Failed to load template for '{prompt_type}': {e}")
            raise e

        # Render template with the current memory state as context.
        rendered_prompt = template.render(CURRENT_MEMORY_STATE=json.dumps(self.memory_state, indent=2))

        # For episodic prompts, update the episode counter.
        if prompt_type == "dreamscape":
            current_counter = entry.get("episode_counter", 1)
            entry["episode_counter"] = current_counter + 1
            logger.info(f"🔢 Dreamscape episode counter updated to {entry['episode_counter']}")
            self.save_prompts()

        return rendered_prompt

    def get_model(self, prompt_type: str) -> str:
        """
        Retrieve the model associated with a given prompt type.
        """
        entry = self.prompts.get(prompt_type)
        if not entry or "model" not in entry:
            raise ValueError(f"Prompt type '{prompt_type}' lacks an associated model.")
        return entry["model"]

    def list_available_prompts(self) -> list:
        """
        Return all available prompt types.
        """
        return list(self.prompts.keys())

    def preview_prompts(self) -> None:
        """
        Print a summary preview of each prompt.
        """
        with self._lock:
            print("\n=== Prompt Previews ===")
            for prompt_type, data in self.prompts.items():
                prompt_text: str = data.get("prompt", "")
                preview = (prompt_text[:100].replace('\n', ' ') + "..." if len(prompt_text) > 100 else prompt_text)
                print(f"- {prompt_type} ({data.get('model', 'N/A')}): {preview}")

    def add_prompt(self, prompt_type: str, prompt_text: str, model: str) -> None:
        """
        Add or update a prompt.
        """
        with self._lock:
            self.prompts[prompt_type] = {"prompt": prompt_text, "model": model}
            logger.info(f"➕ Added/Updated prompt '{prompt_type}' with model '{model}'")
        self.save_prompts()

    def remove_prompt(self, prompt_type: str) -> None:
        """
        Remove an existing prompt.
        """
        with self._lock:
            if prompt_type in self.prompts:
                del self.prompts[prompt_type]
                logger.info(f"🗑️ Removed prompt '{prompt_type}'")
                self.save_prompts()
            else:
                raise ValueError(f"Prompt type '{prompt_type}' does not exist.")

    def reset_to_defaults(self, backup: bool = True) -> None:
        """
        Reset prompts to default values, optionally backing up current prompts.
        """
        with self._lock:
            if backup:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = f"{self.prompt_file}.backup_{timestamp}"
                try:
                    with open(backup_file, 'w', encoding='utf-8') as file:
                        json.dump(self.prompts, file, indent=4, ensure_ascii=False)
                    logger.info(f"📦 Backup of prompts saved to {backup_file}")
                except Exception as e:
                    logger.error(f"❌ Failed to backup prompts: {e}")
            self.prompts = self._get_default_prompts().copy()
            logger.info("🔄 Prompts reset to defaults.")
            self.save_prompts()

    def export_prompts(self, export_path: str) -> None:
        """
        Export current prompts to a specified file.
        """
        with self._lock:
            try:
                with open(export_path, 'w', encoding='utf-8') as file:
                    json.dump(self.prompts, file, indent=4, ensure_ascii=False)
                logger.info(f"📤 Prompts exported to {export_path}")
            except Exception as e:
                logger.error(f"❌ Failed to export prompts: {e}")

    # ---------------------------
    # PERSISTENT MEMORY MANAGEMENT
    # ---------------------------
    def load_memory_state(self) -> None:
        """
        Load persistent memory state from file.
        """
        with self._lock:
            if os.path.exists(self.memory_file):
                try:
                    with open(self.memory_file, 'r', encoding='utf-8') as file:
                        self.memory_state = json.load(file)
                    logger.info(f"✅ Loaded persistent memory from {self.memory_file}")
                except Exception as e:
                    logger.error(f"❌ Failed to load memory state: {e}")
                    self.memory_state = {"version": 1, "last_updated": None, "data": {}}
            else:
                logger.warning("⚠️ No memory file found. Starting with empty state.")
                self.memory_state = {"version": 1, "last_updated": None, "data": {}}

    def save_memory_state(self) -> None:
        """
        Asynchronously save the current memory state to file.
        """
        self._async_save(self.memory_file, self.memory_state, "memory state")

    def parse_memory_updates(self, file_path: str) -> None:
        """
        Parse structured memory updates from a narrative text file.
        The file is expected to contain a MEMORY_UPDATE block at the bottom in JSON format.
        Extracts this JSON block, merges it into self.memory_state["data"],
        updates version and timestamp, and then archives the processed file.
        Also sends a Discord notification about the new archived episode.
        """
        logger.info("🔍 Parsing structured memory updates from file...")
        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return

        with self._lock:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                updates = self._extract_memory_update_block(content)
                if not updates:
                    logger.error("❌ MEMORY_UPDATE block not found or invalid.")
                    return

                previous_state = json.dumps(self.memory_state, indent=2)
                self._merge_memory_updates(updates)

                self.memory_state["version"] = self.memory_state.get("version", 1) + 1
                self.memory_state["last_updated"] = datetime.now(timezone.utc).isoformat()

                logger.info(f"✅ Memory updated with: {updates}")
                self._log_memory_diff(previous_state, self.memory_state)
                self.save_memory_state()

            except Exception as e:
                logger.error(f"❌ Error processing memory updates: {e}")

            finally:
                self.archive_episode(file_path)
                self.discord_manager.send_message(
                    prompt_type="dreamscape",
                    message=f"📦 New episode archived: {os.path.basename(file_path)}. Memory updated to version {self.memory_state.get('version')}."
                )

    def _extract_memory_update_block(self, content: str) -> Dict[str, Any]:
        """
        Extract and parse the MEMORY_UPDATE JSON block from the content.
        Returns:
            Parsed JSON as a dictionary, or None if extraction fails.
        """
        try:
            match = re.search(r"MEMORY_UPDATE:\s*({.*})", content, re.DOTALL)
            if not match:
                return None
            json_block = match.group(1)
            updates = json.loads(json_block)
            logger.info(f"📦 Extracted MEMORY_UPDATE block: {updates}")
            return updates
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to decode MEMORY_UPDATE JSON: {e}")
            return None

    def _merge_memory_updates(self, updates: Dict[str, Any]) -> None:
        """
        Merge the updates into self.memory_state["data"].
        """
        if "data" not in self.memory_state:
            self.memory_state["data"] = {}

        for key, value in updates.items():
            if isinstance(value, list):
                self.memory_state["data"].setdefault(key, [])
                for item in value:
                    if item not in self.memory_state["data"][key]:
                        self.memory_state["data"][key].append(item)
            elif isinstance(value, dict):
                self.memory_state["data"].setdefault(key, {})
                self.memory_state["data"][key].update(value)
            else:
                self.memory_state["data"][key] = value

        logger.info("🛠️ Merged memory updates into state data.")

    def archive_episode(self, file_path: str) -> None:
        """
        Move the processed episode file to an archive folder for historical reference.
        """
        try:
            archive_dir = os.path.join(os.path.dirname(file_path), "archive")
            os.makedirs(archive_dir, exist_ok=True)
            base_name = os.path.basename(file_path)
            archived_path = os.path.join(archive_dir, base_name)
            os.rename(file_path, archived_path)
            logger.info(f"📦 Archived episode file to: {archived_path}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to archive file {file_path}: {e}")

    def _log_memory_diff(self, previous: str, current: Dict[str, Any]) -> None:
        current_state = json.dumps(current, indent=2)
        logger.info(f"📜 Memory diff:\nPrevious:\n{previous}\n\nUpdated:\n{current_state}")

    def review_memory_log(self) -> Dict[str, Any]:
        logger.info("📖 Reviewing persistent memory log:")
        for key, value in self.memory_state.items():
            logger.info(f"{key}: {value}")
        return self.memory_state

    def _async_save(self, file_path: str, data: Any, data_type: str) -> None:
        def save_task() -> None:
            with self._lock:
                try:
                    with open(file_path, 'w', encoding='utf-8') as file:
                        json.dump(data, file, indent=4, ensure_ascii=False)
                    logger.info(f"💾 {data_type.capitalize()} saved to {file_path}")
                except Exception as e:
                    logger.error(f"❌ Failed to save {data_type}: {e}")
        threading.Thread(target=save_task, daemon=True).start()

    # ---------------------------
    # CONTEXTUAL FEEDBACK LOOP MANAGEMENT
    # ---------------------------
    def feedback_loop(self, new_entry: Dict[str, Any]):
        """
        Update context memory with a new interaction.
        """
        logger.info(f"🔁 Processing feedback loop for user: {new_entry.get('user', 'unknown')}")
        user = new_entry.get("user", "unknown")
        platform = new_entry.get("platform", "general")
        ai_output = new_entry.get("ai_output", "")

        with self._lock:
            self.context_memory.setdefault("recent_responses", []).append(new_entry)
            if user != "unknown":
                profile = self.context_memory.setdefault("user_profiles", {}).setdefault(user, {"last_interactions": []})
                profile["last_interactions"].append(new_entry)
            self.context_memory.setdefault("platform_memories", {}).setdefault(platform, []).append(ai_output)

        logger.info(f"✅ Feedback loop updated for {user}.")
        self.save_context_memory_async()

    def save_context_memory_async(self):
        """Asynchronously save the contextual memory database."""
        self._executor.submit(self.save_context_db)

    def save_context_db(self, context_file: str = "memory/context_memory.json"):
        """Save contextual memory to a JSON file."""
        with self._lock:
            try:
                os.makedirs(os.path.dirname(context_file), exist_ok=True)
                with open(context_file, 'w', encoding='utf-8') as f:
                    json.dump(self.context_memory, f, indent=4, ensure_ascii=False)
                logger.info(f"💾 Context memory saved to {context_file}")
            except Exception as e:
                logger.exception(f"❌ Failed to save context memory: {e}")

    def review_context_memory(self):
        """Review and return current context memory."""
        logger.info("📖 Reviewing context memory:")
        for section, entries in self.context_memory.items():
            logger.info(f"{section}: {len(entries)} entries")
        return self.context_memory

    def list_prompts(
        self,
        keyword: str = None,
        model: str = None,
        include_metadata: bool = False,
        sort_by: str = None,
        reverse: bool = False,
        custom_filter: Callable[[str, Dict[str, Any]], bool] = None
    ) -> List[Union[str, Dict[str, Any]]]:
        """
        Return a list of available prompts with optional filtering, sorting, metadata, and custom logic.
        """
        with self._lock:
            prompts_list = []

            for prompt_type, data in self.prompts.items():
                # --- Keyword filter ---
                if keyword and keyword.lower() not in prompt_type.lower():
                    continue

                # --- Model filter ---
                if model and data.get('model') != model:
                    continue

                # --- Custom filter function ---
                if custom_filter and not custom_filter(prompt_type, data):
                    continue

                # --- Metadata structure ---
                if include_metadata:
                    prompt_entry = {
                        'name': prompt_type,
                        'model': data.get('model'),
                        'episode_counter': data.get('episode_counter', None),
                        'prompt_preview': (
                            data.get('prompt', '')[:100] + '...'
                            if len(data.get('prompt', '')) > 100
                            else data.get('prompt', '')
                        ),
                        'length': len(data.get('prompt', '')),
                    }
                    prompts_list.append(prompt_entry)
                else:
                    prompts_list.append(prompt_type)

            # --- Sorting logic ---
            if sort_by:
                if include_metadata:
                    if not all(isinstance(entry, dict) and sort_by in entry for entry in prompts_list):
                        logger.warning(f"⚠️ Sort key '{sort_by}' missing in some entries. Sorting may be inconsistent.")
                    prompts_list.sort(key=lambda x: (x.get(sort_by) is not None, x.get(sort_by)), reverse=reverse)
                else:
                    if sort_by == 'name':
                        prompts_list.sort(reverse=reverse)
                    else:
                        logger.warning(f"⚠️ Sort key '{sort_by}' is not applicable for name-only lists. Skipping sort.")

            logger.info(f"📜 Listed {len(prompts_list)} prompts with filters -> keyword: {keyword}, model: {model}, sort_by: {sort_by}")
            return prompts_list

# ---------------------------
# Example Usage for Autonomous Project Building
# ---------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize AletheiaPromptManager with updated memory file path in memory folder.
    from core.AletheiaPromptManager import AletheiaPromptManager  # Adjust import as needed
    manager = AletheiaPromptManager(
        prompt_file="chat_mate/prompts.json",
        memory_file="memory/persistent_memory.json"
    )
    manager.preview_prompts()

    # Simulate processing a narrative file with a MEMORY_UPDATE block.
    test_file = "d:/overnight_scripts/chat_mate/test_episode.txt"
    simulated_response = (
        "EPISODE NARRATIVE:\nVictor embarked on a quest to unify chaotic signals...\n"
        "MEMORY_UPDATE:\n{\"skill_advancements\": [\"System Convergence +1\"], \"quests_completed\": [\"Unified Data Flow\"], \"architect_tier_progression\": \"Tier 2 Unlocked\"}"
    )
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(simulated_response)

    manager.parse_memory_updates(test_file)
    print("\n=== Updated Memory State ===\n")
    print(json.dumps(manager.review_memory_log(), indent=2))
