#!/usr/bin/env python3
"""
Script to find and remove explicit 'import sip' statements from Python files

This utility:
1. Searches for all Python files in the project
2. Removes any explicit 'import sip' statements
3. Replaces them with comments
"""

import os
import re
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SIP_IMPORT_PATTERNS = [
    r'^import\s+sip\s*$',
    r'^from\s+sip\s+import',
    r'^import\s+sip\s+as\s+',
    r'PyQt5\s+import\s+sip',
]

EXCLUDED_DIRS = ['venv', 'test_venv', 'test_venv2', 'test_env', 'clean_venv', 'venv_fix', '.pytest_cache', '__pycache__', '.git']

def find_python_files(directory):
    """Find all .py files in a directory and its subdirectories."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def process_file(file_path, dry_run=True):
    """Process a file to remove sip imports and replace with comments."""
    try:
        # Try UTF-8 first
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            # If UTF-8 fails, try Latin-1
            with open(file_path, 'r', encoding='latin-1') as f:
                lines = f.readlines()
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
            return False

    changes_made = False
    new_lines = []
    for line in lines:
        original_line = line
        is_sip_import = False

        for pattern in SIP_IMPORT_PATTERNS:
            if re.search(pattern, line):
                is_sip_import = True
                changes_made = True
                line = f"# Removed by sip cleaner: {line.strip()}\n"
                logger.info(f"Found sip import in {file_path}: {original_line.strip()}")
                break

        new_lines.append(line)

    if changes_made and not dry_run:
        try:
            # Write with the same encoding we read with
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            logger.info(f"Updated {file_path}")
        except UnicodeEncodeError:
            with open(file_path, 'w', encoding='latin-1') as f:
                f.writelines(new_lines)
            logger.info(f"Updated {file_path} (using latin-1 encoding)")

    return changes_made

def main():
    parser = argparse.ArgumentParser(description="Remove explicit 'import sip' statements")
    parser.add_argument('--directory', '-d', default='interfaces', help="Directory to search")
    parser.add_argument('--dry-run', '-n', action='store_true', help="Don't modify files, just report findings")
    args = parser.parse_args()

    directory = os.path.abspath(args.directory)
    logger.info(f"Searching for Python files in {directory}")

    python_files = find_python_files(directory)
    logger.info(f"Found {len(python_files)} Python files")

    changes_count = 0
    for file_path in python_files:
        if process_file(file_path, args.dry_run):
            changes_count += 1

    if args.dry_run:
        logger.info(f"Dry run completed. Found {changes_count} files with sip imports.")
        if changes_count > 0:
            logger.info("Run without --dry-run to make changes.")
    else:
        logger.info(f"Completed. Updated {changes_count} files.")

if __name__ == "__main__":
    main() 