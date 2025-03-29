import json
import os
import logging
import re
from pathlib import Path


logger = logging.getLogger(__name__)

def _load_command_config():
    try:
        # Dynamically resolve the project root (2 levels up from this file)
        project_root = Path(__file__).resolve().parents[2]
        config_path = project_root / "config" / "command_config.json"

        if not config_path.exists():
            logger.warning(f"Config file not found at: {config_path}")
            return []

        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        commands = data.get("commands", [])
        logger.info(f"✅ Loaded {len(commands)} assistant commands from {config_path.name}")
        return commands

    except Exception as e:
        logger.error(f"❌ Failed to load command_config.json: {e}")
        return []

COMMAND_CONFIG = _load_command_config()



def parse_input(transcript):
    """
    Parses the transcript and matches it to a configured voice command or falls back to heuristics.
    
    Returns:
        {
            "type": "command" | "question" | "idea" | "unknown",
            "action": <action_name if matched>,
            "args": <parsed arguments or []>,
            "payload": <cleaned command text>,
            "raw": <original transcript>
        }
    """
    logger.debug(f"Parsing transcript: {transcript}")
    transcript = transcript.strip()
    if not transcript:
        logger.warning("Empty transcript received.")
        return {"type": "unknown", "action": None, "args": [], "payload": "", "raw": transcript}

    # Match against loaded command config
    lower_transcript = transcript.lower()
    for cmd in COMMAND_CONFIG:
        for trigger in cmd["triggers"]:
            if lower_transcript.startswith(trigger):
                arg_text = transcript[len(trigger):].strip()
                args = [arg_text] if arg_text else []
                logger.info(f"Matched command: {cmd['action']} (trigger: {trigger})")
                return {
                    "type": "command",
                    "action": cmd["action"],
                    "args": args,
                    "payload": transcript,
                    "raw": transcript
                }

    # Fallback heuristic
    if transcript.endswith("?"):
        return {"type": "question", "action": None, "args": [], "payload": transcript, "raw": transcript}
    
    command_keywords = ["run", "generate", "update", "execute", "start", "stop", "install", "commit", "build"]
    first_word = transcript.split()[0].lower()
    if first_word in command_keywords:
        logger.info(f"Heuristic match as command: {transcript}")
        return {"type": "command", "action": None, "args": [], "payload": transcript, "raw": transcript}

    logger.info(f"Classified as idea: {transcript}")
    return {"type": "idea", "action": None, "args": [], "payload": transcript, "raw": transcript}
