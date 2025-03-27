
import os
import shutil
import argparse

# Files and folders marked for deletion
TARGETS = [
    "clean_venv",
    "chat_mate/tests/test_simple.py",
    "chat_mate/tests/__init__.py",
    "fix_pyqt_sip.py",
    "run_pyqt_without_sip.py",
    "install_dev.py",
    "verify_env.py",
    "cleanup_sip_imports.py"
]

def delete_path(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
        print(f"Deleted folder: {path}")
    elif os.path.isfile(path):
        os.remove(path)
        print(f"Deleted file: {path}")
    else:
        print(f"Not found (skipped): {path}")

def main(dry_run=False):
    for target in TARGETS:
        if dry_run:
            print(f"[Dry Run] Would delete: {target}")
        else:
            delete_path(target)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup unused or redundant files.")
    parser.add_argument("--dry-run", action="store_true", help="List files to delete without deleting.")
    args = parser.parse_args()
    main(dry_run=args.dry_run)