import os
import json
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
import logging
from datetime import datetime

class StartupValidator:
    """
    Validates core system requirements during startup.
    Checks paths, configs, memory files, and environment variables.
    """
    def __init__(self, path_manager, logger: logging.Logger = None):
        self.path_manager = path_manager
        self.logger = logger or logging.getLogger(__name__)
        self.errors = []
        self.warnings = []

    def run_all_checks(self) -> Dict[str, List[str]]:
        """Run all startup validation checks."""
        self.logger.info("🚀 Running startup self-check...")
        
        self.check_env_vars(["STOCKTWITS_USERNAME", "STOCKTWITS_PASSWORD"])
        self.check_paths()
        self.check_memory_files()
        self.check_template_dir()

        if self.errors:
            self.logger.error(f"❌ {len(self.errors)} startup errors detected.")
        else:
            self.logger.info("✅ All core systems validated.")

        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "status": "failed" if self.errors else "success"
        }

    def check_env_vars(self, required_vars: List[str]):
        """Validate required environment variables."""
        load_dotenv()
        for var in required_vars:
            if not os.getenv(var):
                self.warnings.append(f"Missing env var: {var}")
                self.logger.warning(f"⚠️ Missing environment variable: {var}")

    def check_paths(self):
        """Validate existence of required paths and files."""
        required_paths = [
            ("config", self.path_manager.get_config_path()),
            ("memory", self.path_manager.get_memory_path()),
            ("templates", self.path_manager.get_template_path())
        ]

        for name, path in required_paths:
            if not path.exists():
                self.errors.append(f"Missing {name} directory: {path}")
                self.logger.error(f"❌ Required directory missing: {path}")

    def check_memory_files(self):
        """Validate memory files structure and content."""
        self.logger.debug("Starting memory file check...")
        memory_path = Path(self.path_manager.get_path('memory')) / "memory_store.json"
        self.logger.debug(f"Memory file path set to: {memory_path}")
        
        # Create default structure
        default_structure = {
            "version": 1,
            "last_updated": datetime.now().isoformat(),
            "conversations": [],
            "memory": {
                "chat": {
                    "history": [],
                    "context": {},
                    "metadata": {
                        "total_conversations": 0,
                        "last_conversation_id": 0
                    }
                },
                "dreamscape": {
                    "episodes": [],
                    "themes": [],
                    "characters": [],
                    "realms": [],
                    "quests": [],
                    "skill_levels": []
                },
                "system": {
                    "startup_time": datetime.now().isoformat(),
                    "last_sync": None,
                    "services": {
                        "chat_manager": {
                            "status": "initialized",
                            "error": None
                        },
                        "cycle_service": {
                            "status": "initialized",
                            "error": None
                        },
                        "task_orchestrator": {
                            "status": "initialized",
                            "error": None
                        },
                        "dreamscape_generator": {
                            "status": "initialized",
                            "error": None
                        }
                    }
                }
            }
        }

        # Ensure memory directory exists
        self.logger.debug(f"Ensuring memory directory exists: {memory_path.parent}")
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Memory directory confirmed: {memory_path.parent}")

        # If file doesn't exist or is empty, create it with default structure
        self.logger.debug(f"Checking existence and size of {memory_path}")
        if not memory_path.exists() or memory_path.stat().st_size == 0:
            self.logger.info(f"Creating new memory file at: {memory_path}")
            try:
                with open(memory_path, "w", encoding="utf-8") as f:
                    json.dump(default_structure, f, indent=2)
                self.logger.debug(f"Successfully wrote default structure to {memory_path}")
            except Exception as e:
                self.errors.append(f"Failed to create/write memory file: {e}")
                self.logger.error(f"❌ Failed to create/write memory file {memory_path}: {e}")
            return
        self.logger.debug(f"Memory file {memory_path} exists and is not empty.")

        # Validate existing file
        self.logger.debug(f"Attempting to read existing memory file: {memory_path}")
        try:
            with open(memory_path, "r", encoding="utf-8") as f:
                self.logger.debug(f"Reading content from {memory_path}")
                content = f.read().strip()
                self.logger.debug(f"Finished reading content from {memory_path}")
                if not content:
                    self.logger.warning("Memory file is empty, initializing with default structure")
                    self.logger.debug(f"Attempting to write default structure to empty file: {memory_path}")
                    try:
                        with open(memory_path, "w", encoding="utf-8") as f:
                            json.dump(default_structure, f, indent=2)
                        self.logger.debug(f"Successfully wrote default structure to empty file: {memory_path}")
                    except Exception as e:
                        self.errors.append(f"Failed to write default structure to empty memory file: {e}")
                        self.logger.error(f"❌ Failed to write default structure to empty memory file {memory_path}: {e}")
                else:
                    self.logger.debug("Attempting to parse JSON content.")
                    try:
                        json.loads(content)
                        self.logger.info("✅ Memory file validated successfully")
                    except json.JSONDecodeError as e:
                        self.errors.append(f"Invalid JSON in memory file: {e}")
                        self.logger.error(f"❌ Memory file contains invalid JSON: {e}")
                        # Backup corrupted file
                        backup_path = memory_path.with_suffix('.corrupted')
                        self.logger.debug(f"Attempting to rename corrupted file to {backup_path}")
                        try:
                            memory_path.rename(backup_path)
                            self.logger.warning(f"Backed up corrupted memory file to: {backup_path}")
                        except Exception as rename_e:
                            self.errors.append(f"Failed to backup corrupted memory file: {rename_e}")
                            self.logger.error(f"❌ Failed to rename corrupted memory file {memory_path} to {backup_path}: {rename_e}")
                            # Attempt to continue by writing new file anyway, but log the failure
                        # Create new file with default structure
                        self.logger.debug(f"Attempting to write default structure after backup: {memory_path}")
                        try:
                            with open(memory_path, "w", encoding="utf-8") as f:
                                json.dump(default_structure, f, indent=2)
                            self.logger.debug(f"Successfully wrote default structure after backup: {memory_path}")
                        except Exception as write_e:
                            self.errors.append(f"Failed to write new memory file after backup: {write_e}")
                            self.logger.error(f"❌ Failed to write new memory file {memory_path} after backup attempt: {write_e}")
        except Exception as e:
            self.errors.append(f"Error reading memory file: {e}")
            self.logger.error(f"❌ Error accessing memory file {memory_path}: {e}")
        self.logger.debug("Finished memory file check.")

    def check_template_dir(self):
        """Validate template directory structure and content."""
        template_dir = self.path_manager.get_template_path()
        if not template_dir.exists():
            self.errors.append("Missing templates directory")
            self.logger.error(f"❌ Missing template directory at: {template_dir}")
            return

        templates = list(template_dir.glob("**/*.j2"))
        if not templates:
            self.warnings.append("No templates found")
            self.logger.warning("⚠️ Template directory exists but contains no .j2 files")
        else:
            self.logger.info(f"✅ Found {len(templates)} template files") 
