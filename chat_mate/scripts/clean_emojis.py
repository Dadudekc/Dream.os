#!/usr/bin/env python3
import os
import re
import sys
from typing import Dict, Optional

def remove_emojis(text: str) -> str:
    """Remove emoji characters from a string."""
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\u2600-\u26FF"          # Misc symbols
        u"\u2700-\u27BF"          # Dingbats
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)

def clean_file(file_path: str, backup: bool = True) -> Optional[str]:
    """Clean emojis from a Python file's logging statements."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    # Create backup if requested
    backup_path = None
    if backup:
        backup_path = f"{file_path}.bak"
        with open(file_path, 'r', encoding='utf-8') as src, \
             open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
    
    # Read and clean the file
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    cleaned_lines = []
    for line in lines:
        if 'logger.' in line:
            cleaned_line = remove_emojis(line)
            cleaned_lines.append(cleaned_line)
        else:
            cleaned_lines.append(line)
    
    # Write back the cleaned content
    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(cleaned_lines)
    
    return backup_path

def clean_directory(directory: str, backup: bool = True) -> dict[str, Optional[str]]:
    """Clean emojis from all Python files in a directory and its subdirectories."""
    backup_files = {}
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    backup_path = clean_file(file_path, backup)
                    backup_files[file_path] = backup_path
                except Exception as e:
                    print(f"Error cleaning {file_path}: {e}")
    
    return backup_files

def main():
    """Main entry point for the emoji cleaning script."""
    # Get the project root directory
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    print(f"Starting emoji cleaning process in {project_root}")
    print("Creating backups of all files before modification...")
    
    try:
        # Clean all Python files in the project
        backup_files = clean_directory(project_root, backup=True)
        
        # Print summary
        print("\nCleaning complete!")
        print(f"Processed {len(backup_files)} files")
        print("\nBackup files created:")
        for original, backup in backup_files.items():
            if backup:
                print(f"- {original} -> {backup}")
            else:
                print(f"- {original} (no backup created)")
                
    except Exception as e:
        print(f"Error during cleaning process: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 