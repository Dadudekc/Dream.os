import os
import subprocess
from pathlib import Path

# -----------------------------
# CONFIGURABLE PROJECT SETTINGS
# -----------------------------
PROJECT_NAME = "VictorOS"
AUTHOR = "Victor"
INITIAL_COMMIT_MSG = "Initial commit: VictorOS folder structure and orchestrator setup."

# -----------------------------
# FOLDER STRUCTURE
# -----------------------------
FOLDERS = [
    "orchestrator",
    "agents/TradingAgent/strategies",
    "agents/DebuggerAgent/analyzers",
    "agents/ContentAgent/templates",
    "agents/BuilderAgent",
    "agents/FeedbackLoopAgent",
    "memory",
    "execution_engine",
    "interfaces/cli",
    "interfaces/discord_bot",
    "interfaces/api",
    "utils",
    "config",
    "logs"
]

# -----------------------------
# FILES TO GENERATE (boilerplate)
# -----------------------------
FILES = {
    "README.md": f"# {PROJECT_NAME}\n\nUnified Automation & Execution Core for VictorOS.",
    ".gitignore": "*.pyc\n__pycache__/\n.env\n*.sqlite\nlogs/\nmemory/\n",
    "main.py": (
        "from orchestrator.OrchestratorAgent import OrchestratorAgent\n\n"
        "if __name__ == '__main__':\n"
        "    orchestrator = OrchestratorAgent()\n"
        "    orchestrator.run()\n"
    ),
    "orchestrator/OrchestratorAgent.py": (
        "class OrchestratorAgent:\n"
        "    def __init__(self):\n"
        "        print('VictorOS Orchestrator Initialized')\n\n"
        "    def run(self):\n"
        "        print('Orchestrator Running...')\n"
    ),
    "orchestrator/TaskScheduler.py": "# TaskScheduler logic placeholder\n",
    "orchestrator/AgentManager.py": "# AgentManager logic placeholder\n",
    "agents/TradingAgent/TradingAgent.py": "# TradingAgent core logic placeholder\n",
    "agents/DebuggerAgent/DebuggerAgent.py": "# DebuggerAgent core logic placeholder\n",
    "agents/ContentAgent/ContentAgent.py": "# ContentAgent core logic placeholder\n",
    "agents/BuilderAgent/BuilderAgent.py": "# BuilderAgent core logic placeholder\n",
    "agents/FeedbackLoopAgent/FeedbackLoopAgent.py": "# FeedbackLoopAgent core logic placeholder\n",
    "memory/task_memory.json": "{}\n",
    "memory/execution_logs.json": "{}\n",
    "memory/feedback_loops.json": "{}\n",
    "memory/versioning.json": "{}\n",
    "execution_engine/CodeExecutor.py": "# CodeExecutor logic placeholder\n",
    "execution_engine/ScriptRunner.py": "# ScriptRunner logic placeholder\n",
    "execution_engine/Sandbox.py": "# Sandbox execution placeholder\n",
    "interfaces/cli/cli_interface.py": "# CLI interface placeholder\n",
    "interfaces/discord_bot/discord_interface.py": "# Discord bot interface placeholder\n",
    "interfaces/api/api_interface.py": "# API interface placeholder\n",
    "utils/logger.py": "# Logging utility placeholder\n",
    "utils/file_manager.py": "# File management utilities placeholder\n",
    "utils/config_loader.py": "# Config loader utility placeholder\n",
    "utils/error_handler.py": "# Error handling utility placeholder\n",
    "config/agents_config.json": "{\n    \"active_agents\": []\n}\n",
    "config/system_config.json": "{\n    \"mode\": \"offline\",\n    \"execution_environment\": \"local\"\n}\n",
    "config/llm_config.json": "{\n    \"default_llm\": \"ollama\"\n}\n"
}

# -----------------------------
# SCRIPT EXECUTION
# -----------------------------
def create_folder_structure(base_path: Path):
    for folder in FOLDERS:
        path = base_path / folder
        path.mkdir(parents=True, exist_ok=True)
        print(f"[+] Folder created: {path}")

def create_files(base_path: Path):
    for file, content in FILES.items():
        path = base_path / file
        if not path.exists():
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[+] File created: {path}")

def init_git_repo(base_path: Path):
    try:
        subprocess.run(["git", "init"], cwd=base_path, check=True)
        subprocess.run(["git", "add", "."], cwd=base_path, check=True)
        subprocess.run(["git", "commit", "-m", INITIAL_COMMIT_MSG], cwd=base_path, check=True)
        print("[✅] Git repository initialized and initial commit done.")
    except Exception as e:
        print(f"[❌] Git initialization failed: {e}")

def main():
    base_path = Path.cwd() / PROJECT_NAME
    print(f"\n🚀 Setting up VictorOS project at: {base_path}\n")

    try:
        base_path.mkdir(parents=True, exist_ok=True)
        create_folder_structure(base_path)
        create_files(base_path)
        init_git_repo(base_path)

        print(f"\n🎉 {PROJECT_NAME} setup complete!\n")
        print("Next Steps:")
        print(f"1. cd {PROJECT_NAME}")
        print("2. Start building agents or run main.py")
    except Exception as e:
        print(f"[❌] Setup failed: {e}")

if __name__ == "__main__":
    main()
