#!/usr/bin/env python3

import os
import subprocess
import json
from pathlib import Path

# Config
CORE_DIR = Path("core")
DISPATCHER = Path("core/refactor/cursor_dispatcher.py")
OUTPUT_LOG = Path("cursor_prompts/outputs/test_audit_log.json")
SKIP_PATTERNS = ["__init__.py", ".ipynb", "test_", "deprecated"]

def is_testable_python_file(path: Path) -> bool:
    if not path.is_file() or not path.suffix == ".py":
        return False
    return not any(skip in path.name for skip in SKIP_PATTERNS)

def run_cursor_test(file_path: Path) -> dict:
    print(f"🔍 Testing {file_path}...")
    result = subprocess.run([
        "python", str(DISPATCHER),
        "--mode", "test",
        "--file", str(file_path)
    ], capture_output=True, text=True)

    output = result.stdout + result.stderr
    success = "Ran 0 tests" not in output and "FAILED" not in output and result.returncode == 0

    return {
        "file": str(file_path),
        "success": success,
        "zero_tests": "Ran 0 tests" in output,
        "output": output.strip(),
        "returncode": result.returncode
    }

def append_log(log: dict):
    OUTPUT_LOG.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT_LOG.exists():
        try:
            existing = json.loads(OUTPUT_LOG.read_text())
        except:
            existing = []
    else:
        existing = []
    existing.append(log)
    OUTPUT_LOG.write_text(json.dumps(existing, indent=2))

def main():
    print("🚀 Auto Test Maker Initiated")
    all_py_files = list(CORE_DIR.rglob("*.py"))
    testable_files = [f for f in all_py_files if is_testable_python_file(f)]

    for file_path in testable_files:
        result = run_cursor_test(file_path)
        append_log(result)

        if result["zero_tests"]:
            print(f"⚠️  Zero tests detected in: {file_path.name}")
            # You can optionally trigger a second pass here to regenerate stricter test prompt
            # Or flag it for manual inspection

        elif not result["success"]:
            print(f"❌ Test failed in: {file_path.name}")
            print(result["output"])

        else:
            print(f"✅ Passed: {file_path.name}")

    print("✅ Auto Test Audit Complete. Log saved to:", OUTPUT_LOG)

if __name__ == "__main__":
    main()
