#!/usr/bin/env python3
"""
Script to find and update imports of the old DreamscapeGenerationTab.
This script will:
1. Find all Python files that import the old DreamscapeGenerationTab
2. Update the imports to use the new path
3. Create a backup of each modified file
4. Generate a report of all changes
"""

import os
import re
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

def find_files_with_old_import(root_dir: Path) -> List[Path]:
    """Find all Python files that import the old DreamscapeGenerationTab."""
    old_import_patterns = [
        r'from\s+archive\.gui_old\.tabs\.DreamscapeGenerationTab\s+import',
        r'from\s+archive\.gui_old\.tabs\s+import\s+DreamscapeGenerationTab',
        r'import\s+archive\.gui_old\.tabs\.DreamscapeGenerationTab'
    ]
    
    python_files = []
    for pattern in old_import_patterns:
        for file in root_dir.rglob("*.py"):
            if file.is_file() and not any(p in str(file) for p in ["venv", "__pycache__", ".pytest_cache"]):
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if re.search(pattern, content):
                        python_files.append(file)
    
    return list(set(python_files))  # Remove duplicates

def backup_file(file_path: Path) -> Path:
    """Create a backup of a file with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = file_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    backup_path = backup_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
    shutil.copy2(file_path, backup_path)
    return backup_path

def update_imports(file_path: Path) -> Tuple[int, List[str]]:
    """Update old imports to use the new path. Returns (num_changes, old_lines)."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_lines = []
    
    # Pattern 1: Direct import
    pattern1 = r'from\s+archive\.gui_old\.tabs\.DreamscapeGenerationTab\s+import\s+DreamscapeGenerationTab'
    if re.search(pattern1, content):
        old_lines.extend(re.findall(pattern1, content))
        content = re.sub(
            pattern1,
            'from interfaces.pyqt.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab',
            content
        )
    
    # Pattern 2: Import from package
    pattern2 = r'from\s+archive\.gui_old\.tabs\s+import\s+DreamscapeGenerationTab'
    if re.search(pattern2, content):
        old_lines.extend(re.findall(pattern2, content))
        content = re.sub(
            pattern2,
            'from interfaces.pyqt.tabs.DreamscapeGenerationTab import DreamscapeGenerationTab',
            content
        )
    
    # Pattern 3: Full import
    pattern3 = r'import\s+archive\.gui_old\.tabs\.DreamscapeGenerationTab'
    if re.search(pattern3, content):
        old_lines.extend(re.findall(pattern3, content))
        content = re.sub(
            pattern3,
            'import interfaces.pyqt.tabs.DreamscapeGenerationTab',
            content
        )
    
    num_changes = len(old_lines)
    if num_changes > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return num_changes, old_lines

def main():
    """Main function to find and update imports."""
    project_root = Path(__file__).parent.parent
    
    print("🔍 Searching for files with old imports...")
    files = find_files_with_old_import(project_root)
    
    if not files:
        print("✨ No files found with old imports!")
        return 0
    
    print(f"\nFound {len(files)} file(s) with old imports:")
    for file in files:
        print(f"  - {file.relative_to(project_root)}")
    
    # Ask for confirmation
    response = input("\nDo you want to update these files? [y/N] ")
    if response.lower() != 'y':
        print("❌ Operation cancelled.")
        return 1
    
    print("\n🔄 Updating imports...")
    report = []
    
    for file in files:
        try:
            # Create backup
            backup_path = backup_file(file)
            
            # Update imports
            num_changes, old_lines = update_imports(file)
            
            report.append({
                'file': file.relative_to(project_root),
                'backup': backup_path.relative_to(project_root),
                'changes': num_changes,
                'old_lines': old_lines
            })
            
            print(f"✅ Updated {file.relative_to(project_root)} ({num_changes} changes)")
            
        except Exception as e:
            print(f"❌ Error updating {file}: {e}")
    
    # Generate report
    print("\n📝 Update Report:")
    print("-" * 80)
    for entry in report:
        print(f"\nFile: {entry['file']}")
        print(f"Backup: {entry['backup']}")
        print(f"Changes: {entry['changes']}")
        if entry['old_lines']:
            print("Old imports:")
            for line in entry['old_lines']:
                print(f"  {line}")
    print("-" * 80)
    
    print("""
✨ Import update complete!

Next steps:
1. Review the changes in each updated file
2. Run your tests to ensure everything works
3. If you need to restore a file, you can find backups in the 'backups' directory

To test the changes:
```bash
python -m pytest tests/
```

If you encounter any issues:
1. Restore the backup
2. Check the migration guide: docs/migrations/dreamscape_tab_migration.md
3. File an issue with the tag 'migration-support'
""")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 