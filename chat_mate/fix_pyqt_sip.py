#!/usr/bin/env python3
"""
PyQt5 SIP Fix Script

This script scans for all explicit imports of 'sip' in Python files and removes them.
In newer versions of PyQt5, sip is embedded within PyQt5 and explicit imports cause errors.

Usage:
    python fix_pyqt_sip.py
"""

import os
import re
import sys
import argparse
import logging
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Patterns to find explicit sip imports
SIP_IMPORT_PATTERNS = [
    r'^import\s+sip\s*$',                  # import sip
    r'^from\s+sip\s+import',               # from sip import ...
    r'^import\s+sip\s+as\s+',              # import sip as ...
    r'from\s+PyQt5\s+import\s+sip\s*',     # from PyQt5 import sip
]

# Directories to exclude from scanning
EXCLUDE_DIRS = [
    'venv', '.venv', 'env', '.env', 'virtualenv', 
    'test_venv', 'test_venv2', 'test_env', 'clean_venv', 'venv_fix',
    '__pycache__', '.git', '.github', '.idea', '.vscode', 
    'node_modules', 'build', 'dist', '.pytest_cache'
]

def find_pyqt_files(directory, max_files=1000):
    """Find Python files that might be using PyQt5."""
    pyqt_files = []
    
    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            if not file.endswith('.py'):
                continue
                
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # If the file contains PyQt5 imports, scan it for sip imports
                if 'PyQt5' in content:
                    pyqt_files.append(file_path)
                    if len(pyqt_files) >= max_files:
                        logger.warning(f"Reached maximum file limit of {max_files}")
                        return pyqt_files
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
                    if 'PyQt5' in content:
                        pyqt_files.append(file_path)
                except Exception as e:
                    logger.warning(f"Could not read {file_path}: {e}")
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")
                
    return pyqt_files

def fix_file(file_path, dry_run=True):
    """Remove sip imports from a file and back it up."""
    try:
        # Try different encodings
        for encoding in ['utf-8', 'latin-1']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    lines = f.readlines()
                file_encoding = encoding
                break
            except UnicodeDecodeError:
                continue
        else:
            logger.warning(f"Could not read {file_path} with supported encodings")
            return False
            
        # Create backup
        backup_path = f"{file_path}.bak"
        if not dry_run:
            with open(backup_path, 'w', encoding=file_encoding) as f:
                f.writelines(lines)
            logger.info(f"Created backup: {backup_path}")
        
        # Process lines
        new_lines = []
        changes_made = False
        
        for line in lines:
            skip_line = False
            
            for pattern in SIP_IMPORT_PATTERNS:
                if re.search(pattern, line):
                    changes_made = True
                    skip_line = True
                    logger.info(f"Found sip import in {file_path}: {line.strip()}")
                    new_lines.append(f"# Removed by PyQt5-sip fix: {line}")
                    break
            
            if not skip_line:
                new_lines.append(line)
        
        # Write changes
        if changes_made and not dry_run:
            with open(file_path, 'w', encoding=file_encoding) as f:
                f.writelines(new_lines)
            logger.info(f"Updated {file_path}")
            
        return changes_made
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return False

def create_init_file(directory):
    """Create a proper __init__.py file with sip patch for PyQt directories."""
    # First check if we're in a PyQt directory
    for child in Path(directory).glob('*.py'):
        try:
            with open(child, 'r', encoding='utf-8') as f:
                content = f.read()
            if 'PyQt5' in content and 'import' in content:
                # This is a PyQt directory
                init_path = Path(directory) / '__init__.py'
                if init_path.exists():
                    # Check if we should update it
                    with open(init_path, 'r', encoding='utf-8') as f:
                        init_content = f.read()
                    if 'patch_sip_imports' not in init_content:
                        logger.info(f"Updating __init__.py in {directory}")
                        with open(init_path, 'w', encoding='utf-8') as f:
                            f.write('''# Monkey patch to prevent sip import issues
import sys
import types

# Create a dummy sip module to prevent imports from failing
if 'sip' not in sys.modules:
    sys.modules['sip'] = types.ModuleType('sip')
    sys.modules['sip'].setapi = lambda *args, **kwargs: None
    
# Map PyQt5.sip to our dummy module
if 'PyQt5.sip' not in sys.modules:
    sys.modules['PyQt5.sip'] = sys.modules['sip']

''')
                            # Append existing content
                            f.write(init_content)
                    return True
                else:
                    # Create a new one
                    logger.info(f"Creating __init__.py in {directory}")
                    with open(init_path, 'w', encoding='utf-8') as f:
                        f.write('''# Monkey patch to prevent sip import issues
import sys
import types

# Create a dummy sip module to prevent imports from failing
if 'sip' not in sys.modules:
    sys.modules['sip'] = types.ModuleType('sip')
    sys.modules['sip'].setapi = lambda *args, **kwargs: None
    
# Map PyQt5.sip to our dummy module
if 'PyQt5.sip' not in sys.modules:
    sys.modules['PyQt5.sip'] = sys.modules['sip']
''')
                    return True
                
                break
        except Exception:
            pass
            
    return False

def ensure_pyqt5_sip_installed():
    """Try to ensure PyQt5-sip is properly installed."""
    try:
        import PyQt5
        try:
            from PyQt5 import QtCore
            logger.info(f"Found PyQt5 version {QtCore.QT_VERSION_STR}")
        except ImportError:
            logger.warning("Could not import PyQt5.QtCore, PyQt5 installation may be corrupted")
            logger.warning("Continuing anyway...")
        
        try:
            # Try importing sip from PyQt5
            from PyQt5 import sip
            logger.info(f"PyQt5.sip is properly installed ({sip.SIP_VERSION_STR})")
            return True
        except (ImportError, AttributeError) as e:
            logger.warning(f"PyQt5.sip not properly installed: {e}")
            logger.warning("Attempting to fix by upgrading PyQt5-sip...")
            
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "PyQt5-sip"])
            logger.info("Continuing with fixing explicit sip imports regardless of the result")
            return True  # Continue anyway
    except ImportError:
        logger.warning("PyQt5 is not installed, but we'll continue fixing sip imports")
        return True  # Continue anyway

def main():
    parser = argparse.ArgumentParser(description="Fix PyQt5 sip import issues")
    parser.add_argument("--dir", "-d", default=".", help="Directory to scan")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Don't make any changes")
    parser.add_argument("--recursive", "-r", action="store_true", help="Scan subdirectories for PyQt files")
    parser.add_argument("--force", "-f", action="store_true", help="Skip dependency checks")
    args = parser.parse_args()
    
    logger.info("PyQt5-sip Fix Tool")
    
    # Check if PyQt5-sip is properly installed (skip if --force)
    if not args.force:
        ensure_pyqt5_sip_installed()
        
    directory = os.path.abspath(args.dir)
    logger.info(f"Scanning directory: {directory}")
    
    # Find files to process
    pyqt_files = find_pyqt_files(directory)
    logger.info(f"Found {len(pyqt_files)} PyQt files to scan")
    
    # Process files
    changes_count = 0
    for file_path in pyqt_files:
        if fix_file(file_path, args.dry_run):
            changes_count += 1
            
    # Create or update __init__.py files in PyQt directories
    if args.recursive and not args.dry_run:
        init_count = 0
        for root, dirs, _ in os.walk(directory):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for d in dirs:
                subdir = os.path.join(root, d)
                if create_init_file(subdir):
                    init_count += 1
                    
        logger.info(f"Updated {init_count} __init__.py files")
    
    if args.dry_run:
        logger.info(f"DRY RUN: Would have modified {changes_count} files")
        if changes_count > 0:
            logger.info("Run without --dry-run to apply changes")
    else:
        logger.info(f"Modified {changes_count} files")
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 