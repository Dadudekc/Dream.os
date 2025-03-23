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
memory_path = os.path.join(ROOT_DIR, "memory")

logger.info(f"ROOT_DIR is set to: {ROOT_DIR}")
logger.info(f"Jinja2 template path is set to: {template_path}")
logger.info(f"Memory path is set to: {memory_path}")

# Ensure memory directory exists
os.makedirs(memory_path, exist_ok=True)

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
      - Template-based prompt generation using Jinja2
      - Adaptive structured memory updates
      - FULL SYNC integration with Victor.OS
      - Auto-dispatch of Discord notifications on episode archiving
    Managed by Aletheia (Thea).
    """

    def __init__(self, memory_file: str = 'memory/persistent_memory.json'):
        self.memory_file: str = os.path.join(ROOT_DIR, memory_file)
        self.template_path: str = template_path
        self.conversation_memory_file = os.path.join(memory_path, 'conversation_memory.json')
        self.cycle_memory_file = os.path.join(memory_path, 'prompt_cycles.json')

        # Initialize persistent memory states
        self.memory_state: Dict[str, Any] = {
            "version": 1,
            "last_updated": None,
            "data": {}  # Domain-specific data goes here.
        }
        
        self.conversation_memory: Dict[str, Any] = {
            "version": 1,
            "conversations": [],
            "last_conversation_id": 0
        }
        
        self.cycle_memory: Dict[str, Any] = {
            "version": 1,
            "cycles": {},
            "last_cycle_id": 0
        }
        
        self._lock = threading.Lock()

        # Initialize Jinja2 Environment
        self.jinja_env = Environment(loader=FileSystemLoader(template_path))

        # Initialize DiscordManager for notifications.
        self.discord_manager = DiscordManager()

        logger.info(f" Aletheia initializing with memory file: {self.memory_file}")
        logger.info(f" Loading templates from: {self.template_path}")

        # Load all memory states
        self.load_all_memory_states()

    def load_all_memory_states(self) -> None:
        """Load all memory states from their respective files."""
        self.load_memory_state()
        self.load_conversation_memory()
        self.load_cycle_memory()

    def save_all_memory_states(self) -> None:
        """Save all memory states to their respective files."""
        self.save_memory_state()
        self.save_conversation_memory()
        self.save_cycle_memory()

    def start_conversation_cycle(self, cycle_type: str) -> str:
        """Start a new conversation cycle and return its ID."""
        with self._lock:
            cycle_id = f"cycle_{self.cycle_memory['last_cycle_id'] + 1}"
            self.cycle_memory['last_cycle_id'] += 1
            self.cycle_memory['cycles'][cycle_id] = {
                "type": cycle_type,
                "start_time": datetime.now(timezone.utc).isoformat(),
                "conversations": [],
                "memory_state_version": self.memory_state["version"]
            }
            self.save_cycle_memory()
            logger.info(f"Started new conversation cycle: {cycle_id} of type: {cycle_type}")
            return cycle_id

    def end_conversation_cycle(self, cycle_id: str) -> None:
        """End a conversation cycle and update memory state."""
        with self._lock:
            if cycle_id in self.cycle_memory['cycles']:
                cycle = self.cycle_memory['cycles'][cycle_id]
                cycle['end_time'] = datetime.now(timezone.utc).isoformat()
                self._merge_cycle_memory_updates(cycle_id)
                self.save_all_memory_states()
                logger.info(f"Ended conversation cycle: {cycle_id}")
            else:
                logger.warning(f"Attempted to end non-existent cycle: {cycle_id}")

    def record_conversation(self, cycle_id: str, prompt_type: str, response: str) -> str:
        """Record a conversation and return its ID."""
        with self._lock:
            conv_id = f"conv_{self.conversation_memory['last_conversation_id'] + 1}"
            self.conversation_memory['last_conversation_id'] += 1
            
            conversation = {
                "id": conv_id,
                "cycle_id": cycle_id,
                "prompt_type": prompt_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "response": response,
                "memory_updates": self._extract_memory_update_block(response)
            }
            
            self.conversation_memory['conversations'].append(conversation)
            
            if cycle_id in self.cycle_memory['cycles']:
                self.cycle_memory['cycles'][cycle_id]['conversations'].append(conv_id)
            
            self.save_conversation_memory()
            self.save_cycle_memory()
            
            logger.info(f"Recorded conversation: {conv_id} in cycle: {cycle_id}")
            return conv_id

    def get_prompt(self, prompt_type: str, cycle_id: str = None) -> str:
        """
        Retrieve and render the prompt for a given type using a Jinja2 template.
        Optionally associates the prompt with a conversation cycle.
        """
        try:
            template = self.jinja_env.get_template(f"{prompt_type}.j2")
            
            context = {
                "CURRENT_MEMORY_STATE": json.dumps(self.memory_state, indent=2),
                "TIMESTAMP": datetime.now(timezone.utc).isoformat()
            }
            
            if cycle_id and cycle_id in self.cycle_memory['cycles']:
                cycle = self.cycle_memory['cycles'][cycle_id]
                context["CYCLE_CONTEXT"] = json.dumps(cycle, indent=2)
            
            rendered_prompt = template.render(**context)
            return rendered_prompt
        except Exception as e:
            logger.error(f" Failed to load or render template for '{prompt_type}': {e}")
            raise e

    def load_conversation_memory(self) -> None:
        """Load conversation memory from file."""
        self._load_json_file(self.conversation_memory_file, self.conversation_memory, "conversation memory")

    def save_conversation_memory(self) -> None:
        """Save conversation memory to file."""
        self._async_save(self.conversation_memory_file, self.conversation_memory, "conversation memory")

    def load_cycle_memory(self) -> None:
        """Load cycle memory from file."""
        self._load_json_file(self.cycle_memory_file, self.cycle_memory, "cycle memory")

    def save_cycle_memory(self) -> None:
        """Save cycle memory to file."""
        self._async_save(self.cycle_memory_file, self.cycle_memory, "cycle memory")

    def _load_json_file(self, file_path: str, default_state: Dict[str, Any], state_name: str) -> None:
        """Generic JSON file loader with proper error handling."""
        with self._lock:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        loaded_state = json.load(file)
                        default_state.update(loaded_state)
                    logger.info(f" Loaded {state_name} from {file_path}")
                except Exception as e:
                    logger.error(f" Failed to load {state_name}: {e}")
            else:
                logger.warning(f"️ No {state_name} file found at {file_path}. Using default state.")

    def _merge_cycle_memory_updates(self, cycle_id: str) -> None:
        """Merge all memory updates from a conversation cycle into the main memory state."""
        cycle = self.cycle_memory['cycles'].get(cycle_id)
        if not cycle:
            return

        updates = {}
        for conv_id in cycle['conversations']:
            for conv in self.conversation_memory['conversations']:
                if conv['id'] == conv_id and conv['memory_updates']:
                    self._merge_memory_updates(conv['memory_updates'])

        self.memory_state["version"] += 1
        self.memory_state["last_updated"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"Merged memory updates from cycle {cycle_id}")

    def list_available_prompts(self) -> list:
        """
        Return all available prompt types by scanning the template directory.
        """
        try:
            templates = [f.replace('.j2', '') for f in os.listdir(self.template_path) if f.endswith('.j2')]
            return templates
        except Exception as e:
            logger.error(f" Failed to list templates: {e}")
            return []

    def load_memory_state(self) -> None:
        """
        Load persistent memory state from file.
        """
        with self._lock:
            if os.path.exists(self.memory_file):
                try:
                    with open(self.memory_file, 'r', encoding='utf-8') as file:
                        self.memory_state = json.load(file)
                    logger.info(f" Loaded persistent memory from {self.memory_file}")
                except Exception as e:
                    logger.error(f" Failed to load memory state: {e}")
                    self.memory_state = {"version": 1, "last_updated": None, "data": {}}
            else:
                logger.warning("️ No memory file found. Starting with empty state.")
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
        logger.info(" Parsing structured memory updates from file...")
        if not os.path.exists(file_path):
            logger.error(f" File not found: {file_path}")
            return

        with self._lock:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                updates = self._extract_memory_update_block(content)
                if not updates:
                    logger.error(" MEMORY_UPDATE block not found or invalid.")
                    return

                previous_state = json.dumps(self.memory_state, indent=2)
                self._merge_memory_updates(updates)

                self.memory_state["version"] = self.memory_state.get("version", 1) + 1
                self.memory_state["last_updated"] = datetime.now(timezone.utc).isoformat()

                logger.info(f" Memory updated with: {updates}")
                self._log_memory_diff(previous_state, self.memory_state)
                self.save_memory_state()

            except Exception as e:
                logger.error(f" Error processing memory updates: {e}")

            finally:
                self.archive_episode(file_path)
                self.discord_manager.send_message(
                    prompt_type="dreamscape",
                    message=f"📦 New episode archived: {os.path.basename(file_path)}. Memory updated to version {self.memory_state.get('version')}."
                )

    def _extract_memory_update_block(self, content: str) -> Dict[str, Any]:
        """Extract the MEMORY_UPDATE block from a response and parse it as JSON."""
        try:
            # Look for MEMORY_UPDATE block in the content
            pattern = r"MEMORY_UPDATE:?\s*({[\s\S]*?})"
            match = re.search(pattern, content)
            
            if not match:
                logger.warning("No MEMORY_UPDATE block found in response")
                return {}
            
            # Extract and parse the JSON block
            json_str = match.group(1).strip()
            updates = json.loads(json_str)
            
            logger.info(f"Extracted memory updates: {updates}")
            return updates
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse MEMORY_UPDATE block: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error extracting memory updates: {e}")
            return {}

    def _merge_memory_updates(self, updates: Dict[str, Any]) -> None:
        """Merge memory updates into the current memory state."""
        with self._lock:
            try:
                for key, value in updates.items():
                    if isinstance(value, list):
                        # Initialize the key if it doesn't exist
                        if key not in self.memory_state["data"]:
                            self.memory_state["data"][key] = []
                        
                        # Append new items, avoiding duplicates
                        current_list = self.memory_state["data"][key]
                        for item in value:
                            if item not in current_list:
                                current_list.append(item)
                                
                    elif isinstance(value, dict):
                        # Deep merge dictionaries
                        if key not in self.memory_state["data"]:
                            self.memory_state["data"][key] = {}
                        self.memory_state["data"][key].update(value)
                        
                    else:
                        # For scalar values, just update/replace
                        self.memory_state["data"][key] = value
                
                # Update version and timestamp
                self.memory_state["version"] += 1
                self.memory_state["last_updated"] = datetime.now(timezone.utc).isoformat()
                
                logger.info(f"Memory state updated to version {self.memory_state['version']}")
                
            except Exception as e:
                logger.error(f"Error merging memory updates: {e}")
                raise

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
            logger.info(f" Archived episode file to: {archived_path}")
        except Exception as e:
            logger.warning(f"️ Failed to archive file {file_path}: {e}")

    def _log_memory_diff(self, previous: str, current: Dict[str, Any]) -> None:
        current_state = json.dumps(current, indent=2)
        logger.info(f" Memory diff:\nPrevious:\n{previous}\n\nUpdated:\n{current_state}")

    def review_memory_log(self) -> Dict[str, Any]:
        logger.info(" Reviewing persistent memory log:")
        for key, value in self.memory_state.items():
            logger.info(f"{key}: {value}")
        return self.memory_state

    def _async_save(self, file_path: str, data: Any, data_type: str) -> None:
        def save_task() -> None:
            with self._lock:
                try:
                    with open(file_path, 'w', encoding='utf-8') as file:
                        json.dump(data, file, indent=4, ensure_ascii=False)
                    logger.info(f" {data_type.capitalize()} saved to {file_path}")
                except Exception as e:
                    logger.error(f" Failed to save {data_type}: {e}")
        threading.Thread(target=save_task, daemon=True).start()

# ---------------------------
# Example Usage for Autonomous Project Building
# ---------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize AletheiaPromptManager with updated memory file path in memory folder.
    from core.AletheiaPromptManager import AletheiaPromptManager  # Adjust import as needed
    manager = AletheiaPromptManager(
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
