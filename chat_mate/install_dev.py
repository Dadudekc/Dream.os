#!/usr/bin/env python3
"""
Development Installation Script

This script installs the chat_mate package in development mode,
making imports work correctly without path manipulation.

Run with:
    python install_dev.py
"""

import os
import sys
import subprocess
import platform

def install_package():
    print("Installing chat_mate package in development mode...")
    
    # Determine the command based on the platform
    if platform.system() == "Windows":
        pip_cmd = [sys.executable, "-m", "pip", "install", "-e", "."]
    else:
        pip_cmd = ["pip", "install", "-e", "."]
    
    # Run the installation command
    try:
        subprocess.check_call(pip_cmd)
        print("\n✅ Installation successful!")
        print("\nYou can now import from chat_mate using absolute imports:")
        print("    from core.social.CommunityDashboard import CommunityDashboard")
        print("    from interfaces.pyqt.DreamscapeMainWindow import DreamscapeMainWindow")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Installation failed with error: {e}")
        return False
    
    return True

def main():
    # Check if setup.py exists
    if not os.path.exists("setup.py") and not os.path.exists("pyproject.toml"):
        print("❌ Error: Neither setup.py nor pyproject.toml found in current directory.")
        print("Please run this script from the project root directory.")
        return False
    
    # Install the package
    success = install_package()
    
    if success:
        print("\nYou can now run the application with:")
        print("    python -m interfaces.pyqt.DreamscapeMainWindow")
    
    return success

if __name__ == "__main__":
    sys.exit(0 if main() else 1) 