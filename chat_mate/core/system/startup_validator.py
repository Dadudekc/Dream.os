import os
import json
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
import logging
from datetime import datetime

from chat_mate.core.PathManager import PathManager

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
            ("config", PathManager.get_config_path()),
            ("memory", PathManager.get_memory_path()),
            ("templates", PathManager.get_template_path())
        ]

        for name, path in required_paths:
            if not path.exists():
                self.errors.append(f"Missing {name} directory: {path}")
                self.logger.error(f"❌ Required directory missing: {path}")

    def check_memory_files(self):
        """Validate memory files structure and content."""
        memory_path = Path(self.path_manager.get_path('memory')) / "memory_store.json"
        
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
        memory_path.parent.mkdir(parents=True, exist_ok=True)

        # If file doesn't exist or is empty, create it with default structure
        if not memory_path.exists() or memory_path.stat().st_size == 0:
            self.logger.info(f"Creating new memory file at: {memory_path}")
            with open(memory_path, "w", encoding="utf-8") as f:
                json.dump(default_structure, f, indent=2)
            return

        # Validate existing file
        try:
            with open(memory_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    self.logger.warning("Memory file is empty, initializing with default structure")
                    with open(memory_path, "w", encoding="utf-8") as f:
                        json.dump(default_structure, f, indent=2)
                else:
                    try:
                        json.loads(content)
                        self.logger.info("✅ Memory file validated successfully")
                    except json.JSONDecodeError as e:
                        self.errors.append(f"Invalid JSON in memory file: {e}")
                        self.logger.error(f"❌ Memory file contains invalid JSON: {e}")
                        # Backup corrupted file
                        backup_path = memory_path.with_suffix('.corrupted')
                        memory_path.rename(backup_path)
                        self.logger.warning(f"Backed up corrupted memory file to: {backup_path}")
                        # Create new file with default structure
                        with open(memory_path, "w", encoding="utf-8") as f:
                            json.dump(default_structure, f, indent=2)
        except Exception as e:
            self.errors.append(f"Error reading memory file: {e}")
            self.logger.error(f"❌ Error accessing memory file: {e}")

    def check_template_dir(self):
        """Validate template directory structure and content."""
        template_dir = PathManager.get_template_path()
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
