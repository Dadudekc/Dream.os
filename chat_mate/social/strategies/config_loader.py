import os
import json
import yaml
from dotenv import load_dotenv

# Load .env file variables into the environment
load_dotenv()

# Defaults: the configuration files are expected to be in the 'chat_mate/memory' directory by default.
DEFAULT_CONFIG_DIR = os.path.join('memory')
# Environment variable to override the default config directory
CONFIG_DIR = os.getenv('CHAT_MATE_CONFIG_DIR', DEFAULT_CONFIG_DIR)

JSON_CONFIG_FILE = os.path.join(CONFIG_DIR, 'chat_mate_config.json')
YAML_CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.yml')

# Cached config data (so we don't reload files repeatedly)
_cached_config = {}

def load_yaml_config():
    if os.path.exists(YAML_CONFIG_FILE):
        with open(YAML_CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            print(f"✅ Loaded YAML config: {YAML_CONFIG_FILE}")
            return config
    print(f"⚠️ YAML config file not found: {YAML_CONFIG_FILE}")
    return {}

def load_json_config():
    if os.path.exists(JSON_CONFIG_FILE):
        with open(JSON_CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            print(f"✅ Loaded JSON config: {JSON_CONFIG_FILE}")
            return config
    print(f"⚠️ JSON config file not found: {JSON_CONFIG_FILE}")
    return {}

def load_configs():
    global _cached_config
    # Prioritize YAML config, fallback to JSON
    config_data = load_yaml_config()
    if not config_data:
        config_data = load_json_config()

    _cached_config = config_data
    return config_data

def get_nested(dictionary, nested_key, default=None):
    """Get nested dictionary values by dot notation"""
    keys = nested_key.split('.')
    for key in keys:
        if isinstance(dictionary, dict):
            dictionary = dictionary.get(key)
        else:
            return default
    return dictionary if dictionary is not None else default

def get_env_or_config(key: str, default=None):
    """
    Check in this order:
    1. Environment variables (flat keys, not nested)
    2. YAML/JSON config files (supports nested lookup with dot notation)
    """
    # Priority 1: environment variable
    env_value = os.getenv(key.upper())
    if env_value is not None:
        return env_value
 
    # Priority 2: cached config file data
    if not _cached_config:
        load_configs()

    # Support dot notation in nested config lookup
    return get_nested(_cached_config, key, default)

# Optional utility: refresh/reload configs manually
def reload_configs():
    print("🔄 Reloading config files...")
    return load_configs()

# Preload configs on import
load_configs()
