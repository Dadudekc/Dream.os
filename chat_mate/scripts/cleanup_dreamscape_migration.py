#!/usr/bin/env python3
"""
Script to clean up after successful DreamscapeGenerationTab migration.
This script will:
1. Run all tests to verify the migration
2. Archive the old implementation
3. Remove any backup files older than 30 days
4. Generate a final migration report
"""

import os
import sys
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

def run_tests() -> bool:
    """Run the test suite to verify migration success."""
    print("🧪 Running tests...")
    
    try:
        # Run pytest with detailed output
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-v"],
            capture_output=True,
            text=True
        )
        
        # Print test output
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        
        return result.returncode == 0
    
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def archive_old_implementation(project_root: Path) -> bool:
    """Archive the old DreamscapeGenerationTab implementation."""
    old_file = project_root / "archive" / "gui_old" / "tabs" / "DreamscapeGenerationTab.py"
    if not old_file.exists():
        print("ℹ️ Old implementation already removed.")
        return True
    
    try:
        # Create archive directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir = project_root / "archive" / "deprecated" / f"dreamscape_tab_{timestamp}"
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Move the file to archive
        shutil.move(str(old_file), str(archive_dir / "DreamscapeGenerationTab.py"))
        
        # Create an info file
        with open(archive_dir / "DEPRECATED.md", "w") as f:
            f.write(f"""# Deprecated DreamscapeGenerationTab

This implementation was deprecated on {datetime.now().strftime("%Y-%m-%d")} in favor of:
`interfaces/pyqt/tabs/DreamscapeGenerationTab.py`

See the migration guide at:
`docs/migrations/dreamscape_tab_migration.md`

Original location:
`{old_file.relative_to(project_root)}`
""")
        
        print(f"📦 Archived old implementation to: {archive_dir.relative_to(project_root)}")
        return True
        
    except Exception as e:
        print(f"❌ Error archiving old implementation: {e}")
        return False

def cleanup_old_backups(project_root: Path, days: int = 30) -> Dict[str, int]:
    """Remove backup files older than specified days."""
    cutoff = datetime.now() - timedelta(days=days)
    stats = {"removed": 0, "kept": 0}
    
    # Find all backup directories
    backup_dirs = []
    for path in project_root.rglob("backups"):
        if path.is_dir():
            backup_dirs.append(path)
    
    for backup_dir in backup_dirs:
        for file in backup_dir.glob("*"):
            if not file.is_file():
                continue
            
            # Check if file matches our backup pattern
            if "_2024" in file.name and file.suffix in [".py", ".yaml", ".json"]:
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                if mtime < cutoff:
                    try:
                        file.unlink()
                        stats["removed"] += 1
                    except Exception as e:
                        print(f"⚠️ Could not remove {file}: {e}")
                else:
                    stats["kept"] += 1
    
    return stats

def generate_report(project_root: Path, cleanup_stats: Dict[str, int]) -> None:
    """Generate a final migration report."""
    report_dir = project_root / "docs" / "migrations" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"dreamscape_migration_{timestamp}.md"
    
    with open(report_file, "w") as f:
        f.write(f"""# DreamscapeGenerationTab Migration Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Migration Status

### Tests
✅ All tests passing
- Location: `tests/test_dreamscape_tab_migration.py`
- Run: `python -m pytest tests/`

### Old Implementation
📦 Archived to: `archive/deprecated/dreamscape_tab_{timestamp}/`

### Backup Cleanup
- Removed: {cleanup_stats['removed']} old backup files
- Kept: {cleanup_stats['kept']} recent backup files
- Retention policy: 30 days

## Next Steps

1. Update any remaining imports:
   ```bash
   python scripts/update_dreamscape_imports.py
   ```

2. Review the new features available:
   - Episode metadata caching
   - Integration with AgentDispatcher
   - Real-time Discord feedback

3. Clean up any remaining references:
   ```bash
   git grep -l "archive.gui_old.tabs.DreamscapeGenerationTab"
   ```

## Support

If you encounter any issues:
1. Check the migration guide: `docs/migrations/dreamscape_tab_migration.md`
2. Review test failures in detail
3. File an issue with tag 'migration-support'

## Rollback Instructions

To rollback this migration:
1. Restore the old implementation from: `archive/deprecated/dreamscape_tab_{timestamp}/`
2. Update imports to use the old path
3. Run tests to verify the rollback
""")
    
    print(f"📝 Generated migration report: {report_file.relative_to(project_root)}")

def main():
    """Main cleanup function."""
    project_root = Path(__file__).parent.parent
    
    print("🔄 Starting cleanup process...")
    
    # 1. Run tests
    if not run_tests():
        print("❌ Tests failed! Please fix issues before cleanup.")
        return 1
    
    # 2. Archive old implementation
    if not archive_old_implementation(project_root):
        print("❌ Failed to archive old implementation.")
        return 1
    
    # 3. Clean up old backups
    print("\n🧹 Cleaning up old backup files...")
    cleanup_stats = cleanup_old_backups(project_root)
    print(f"Removed {cleanup_stats['removed']} old backup files, kept {cleanup_stats['kept']} recent ones.")
    
    # 4. Generate report
    generate_report(project_root, cleanup_stats)
    
    print("""
✨ Cleanup complete!

Next steps:
1. Review the migration report
2. Run the import update script if needed
3. Remove any remaining references to the old implementation
4. Commit the changes

To find any remaining references:
```bash
git grep -l "archive.gui_old.tabs.DreamscapeGenerationTab"
```
""")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 