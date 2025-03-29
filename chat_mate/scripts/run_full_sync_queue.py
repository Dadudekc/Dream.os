import argparse
import os
import json
from pathlib import Path
import subprocess
import time

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_QUEUE_DIR = ROOT_DIR / ".cursor" / "queued_tasks"
CURSOR_CLI = "cursor"  # Replace with full path if needed

def run_cursor_queue(queue_path: Path):
    print(f"\n🚀 Running Full Sync Queue: {queue_path.name}")
    try:
        result = subprocess.run(
            [CURSOR_CLI, "run", str(queue_path)],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print(f"❌ STDERR:\n{result.stderr}")
    except Exception as e:
        print(f"❌ Failed to run queue {queue_path.name}: {e}")

def run_all_queues(directory: Path):
    if not directory.exists():
        print(f"❌ Queue directory not found: {directory}")
        return

    queue_files = list(directory.glob("*.json"))
    if not queue_files:
        print(f"⚠️ No queue files found in {directory}")
        return

    print(f"🧭 Found {len(queue_files)} queues in: {directory}")
    for queue_path in queue_files:
        run_cursor_queue(queue_path)
        time.sleep(1)  # Optional delay between runs

def run_queue(queue_path):
    print(f"🚀 Running Full Sync Queue: {os.path.basename(queue_path)}")

    try:
        result = subprocess.run(
            ["cursor", "run", queue_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path.cwd()  # optional, to ensure context
        )
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to run queue {queue_path}: {e.stderr}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", help="Run a specific queue file")
    parser.add_argument("--all", action="store_true", help="Run all queue files in the directory")
    parser.add_argument("--dir", help="Directory to scan for queues", default=str(DEFAULT_QUEUE_DIR))
    args = parser.parse_args()

    queue_dir = Path(args.dir).resolve()

    if args.queue:
        run_cursor_queue(Path(args.queue).resolve())
    elif args.all:
        run_all_queues(queue_dir)
    else:
        print("⚠️ Please provide either --queue or --all.")

if __name__ == "__main__":
    main()
