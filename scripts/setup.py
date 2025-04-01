"""
Setup Script

This script ensures all required directories exist and initializes
any necessary resources for the application.
"""

import os
from pathlib import Path

def create_directories():
    """Create all required directories if they don't exist."""
    directories = [
        "config",
        "core/templates",
        "core/micro_factories",
        "data",
        "logs",
        "memory",
        "interfaces/pyqt/tabs",
        "interfaces/pyqt/components",
        "social",
        "utils"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def create_empty_init_files():
    """Create empty __init__.py files in all directories."""
    for root, dirs, files in os.walk("."):
        if ".git" in root or "venv" in root or "__pycache__" in root:
            continue
            
        init_file = Path(root) / "__init__.py"
        if not init_file.exists():
            init_file.touch()
            print(f"✅ Created __init__.py in: {root}")

def main():
    """Main setup function."""
    print("Setting up Chat Mate project structure...")
    create_directories()
    create_empty_init_files()
    print("\nSetup complete! 🎉")

if __name__ == "__main__":
    main() 