import os
import shutil
from pathlib import Path

# Dead files from the last audit
dead_files = [
    "1.py",
    "ARCHIVE\\__init__.py",
    "__init__.py",
    "chat_mate\\tests\\__init__.py",
    "config\\__init__.py"
]

# Define base and archive destination
PROJECT_ROOT = Path(__file__).resolve().parent
ARCHIVE_DIR = PROJECT_ROOT / "ARCHIVE_BAK"

def archive_file(file_path):
    src = PROJECT_ROOT / file_path
    if not src.exists():
        print(f"❌ Skipped (not found): {src}")
        return
    dest = ARCHIVE_DIR / file_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    print(f"📦 Archived: {file_path} → {dest}")

def main():
    print(f"🔁 Archiving {len(dead_files)} dead files...\n")
    for file in dead_files:
        archive_file(Path(file))
    print("\n✅ Archive complete.")

if __name__ == "__main__":
    main()
