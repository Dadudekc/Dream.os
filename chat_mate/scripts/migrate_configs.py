import os
import json
import yaml
from typing import Dict, Any
import shutil
from datetime import datetime

from core.ConfigManager import ConfigManager
from core.PathManager import PathManager

def load_json_file(filepath: str) -> Dict[str, Any]:
    """Load a JSON file if it exists."""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
    return {}

def load_yaml_file(filepath: str) -> Dict[str, Any]:
    """Load a YAML file if it exists."""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
    return {}

def backup_config_files(files_to_backup: list) -> str:
    """Create backups of existing config files."""
    backup_dir = os.path.join(PathManager.get_path("configs"), "backups", 
                             datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(backup_dir, exist_ok=True)
    
    for filepath in files_to_backup:
        if os.path.exists(filepath):
            filename = os.path.basename(filepath)
            backup_path = os.path.join(backup_dir, filename)
            shutil.copy2(filepath, backup_path)
            print(f"Backed up {filepath} to {backup_path}")
            
    return backup_dir

def migrate_configs():
    """Migrate all existing configurations to ConfigManager."""
    # Initialize the unified config
    config_manager = ConfigManager()
    
    # List of config files to migrate
    config_files = {
        "chat_mate_config.json": os.path.join(PathManager.get_path("memory"), "chat_mate_config.json"),
        "config.yml": os.path.join(PathManager.get_path("memory"), "config.yml"),
        "discord_manager_config.json": "discord_manager_config.json",
        "rate_limit_state.json": os.path.join(PathManager.get_path("memory"), "rate_limit_state.json")
    }
    
    # Create backups
    backup_dir = backup_config_files(list(config_files.values()))
    print(f"Created backups in {backup_dir}")
    
    # Load and merge configurations
    merged_config = {
        "app": {
            "name": "ChatMate",
            "version": "1.0.0",
            "debug": False,
            "log_level": "INFO"
        }
    }
    
    # Load chat_mate_config.json
    chat_mate_config = load_json_file(config_files["chat_mate_config.json"])
    if chat_mate_config:
        merged_config.update({
            "app": {
                **merged_config["app"],
                **chat_mate_config.get("config", {}).get("app", {})
            }
        })
    
    # Load config.yml
    yaml_config = load_yaml_file(config_files["config.yml"])
    if yaml_config:
        # Merge social settings
        social_config = yaml_config.get("social", {})
        merged_config["social"] = {
            **merged_config.get("social", {}),
            **social_config
        }
    
    # Load Discord config
    discord_config = load_json_file(config_files["discord_manager_config.json"])
    if discord_config:
        merged_config["social"]["discord"] = {
            **merged_config.get("social", {}).get("discord", {}),
            **discord_config
        }
    
    # Load rate limits
    rate_limits = load_json_file(config_files["rate_limit_state.json"])
    if rate_limits:
        merged_config["social"]["rate_limits"] = rate_limits
    
    # Add default paths from PathManager
    merged_config["storage"] = {
        "base_path": PathManager.base_dir,
        "outputs_dir": PathManager.outputs_dir,
        "memory_dir": PathManager.memory_dir,
        "templates_dir": PathManager.templates_dir,
        "drivers_dir": PathManager.drivers_dir,
        "configs_dir": PathManager.configs_dir,
        "logs_dir": PathManager.logs_dir
    }
    
    # Merge the configurations
    config_manager.merge(merged_config)
    print("Configuration migration completed successfully!")
    
    # Cleanup old config files (optional)
    should_cleanup = input("Do you want to remove old config files? (yes/no): ").lower()
    if should_cleanup == "yes":
        for filepath in config_files.values():
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    print(f"Removed {filepath}")
                except Exception as e:
                    print(f"Error removing {filepath}: {e}")

if __name__ == "__main__":
    migrate_configs() 