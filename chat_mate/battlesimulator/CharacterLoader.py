import os
import json
from typing import Dict, Any, List


REQUIRED_FIELDS = {"name", "signature_techniques"}


def load_character(name: str, path: str = "battlesimulator/characters") -> Dict[str, Any]:
    """Load a single character profile by name."""
    file_path = os.path.join(path, f"{name}.json")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No character profile found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _validate_profile(data, filename=f"{name}.json")
    return data


def load_all_characters(path: str = "battlesimulator/characters") -> Dict[str, Dict[str, Any]]:
    """Load all valid character profiles in the directory."""
    characters = {}
    for filename in os.listdir(path):
        if filename.endswith(".json"):
            try:
                with open(os.path.join(path, filename), "r", encoding="utf-8") as f:
                    data = json.load(f)
                _validate_profile(data, filename)
                characters[data["name"]] = data
            except Exception as e:
                print(f"[CharacterLoader] Skipped {filename}: {e}")
    return characters


def list_character_names(path: str = "battlesimulator/characters") -> List[str]:
    """Return list of all available character names based on JSON filenames."""
    return [f[:-5] for f in os.listdir(path) if f.endswith(".json")]


def _validate_profile(data: Dict[str, Any], filename: str):
    missing = REQUIRED_FIELDS - data.keys()
    if missing:
        raise ValueError(f"{filename} is missing required fields: {missing}")
    if not isinstance(data["signature_techniques"], list) or not data["signature_techniques"]:
        raise ValueError(f"{filename} must include at least one technique in 'signature_techniques'") 