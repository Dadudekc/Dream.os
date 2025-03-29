DEFAULT_EXCLUDED_CHATS = [
    "ChatGPT", "Sora", "Freeride Investor",
    "Tbow Tactic Generator", "Explore GPTs", "Axiom",
    "work project", "prompt library", "Bot",
    "smartstock-pro", "Code Copilot"
]

def sanitize_filename(filename: str) -> str:
    import re
    return re.sub(r'[\\/*?:"<>| ]+', "_", filename).strip("_")[:50]
