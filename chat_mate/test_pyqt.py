import os
import shutil
from pathlib import Path

# Define project root and backup destination folder
PROJECT_ROOT = Path('D:/overnight_scripts/chat_mate').resolve()
BACKUP_FOLDER = PROJECT_ROOT / 'backup'

def find_and_move_backup_files(dry_run: bool = False):
    """
    Find all .bak and .import_bak files and move them to the backup folder,
    preserving their relative directory structure, but excluding the backup folder itself.
    """
    backup_extensions = ['.bak', '.import_bak']
    moved_files = 0

    print(f"\n[INFO] Scanning project root: {PROJECT_ROOT}")
    print(f"[INFO] Excluding backup folder: {BACKUP_FOLDER}\n")

    # Walk through all files excluding BACKUP_FOLDER
    for file_path in PROJECT_ROOT.rglob('*'):
        # Skip anything inside the backup directory
        if BACKUP_FOLDER in file_path.parents:
            continue
        
        if file_path.is_file() and file_path.suffix in backup_extensions:
            # Compute relative path from project root
            relative_path = file_path.relative_to(PROJECT_ROOT)

            # Destination path under BACKUP_FOLDER
            dest_path = BACKUP_FOLDER / relative_path

            # Ensure destination directory exists
            if not dry_run:
                dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Move file
            if dry_run:
                print(f"[DRY RUN] Would move: {file_path} -> {dest_path}")
            else:
                shutil.move(str(file_path), str(dest_path))
                print(f"[MOVED] {file_path} -> {dest_path}")
            
            moved_files += 1

    print(f"\n[RESULT] {'Dry run complete' if dry_run else 'Move complete'}: {moved_files} files processed.")
    print(f"[RESULT] Backup folder location: {BACKUP_FOLDER}")

if __name__ == '__main__':
    # Set dry_run=True to test without moving
    find_and_move_backup_files(dry_run=False)
