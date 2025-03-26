import json
import os
import logging
import re

logger = logging.getLogger(__name__)

# Load command configuration
def _load_command_config():
    try:
        config_path = os.path.join(
            os.path.dirname(__file__), "config", "command_config.json"
        )
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data.get('commands', []))} assistant commands.")
        return data.get("commands", [])
    except Exception as e:
        logger.error(f"Failed to load command_config.json: {e}")
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
