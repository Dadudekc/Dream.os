#!/usr/bin/env python3
"""
overnight_test_generator_ollama.py

Automates overnight generation and execution of Python unittests using Ollama's deepseek-r1 model.

Improvements:
- Explicit UTF-8 encoding for all file operations.
- AST filtering ensures only testable files (containing classes/functions) are processed.
- Robust error handling and logging.
- Maintains skip list to avoid redundant processing.
- Generates comprehensive JSON reports.

Usage:
    python overnight_test_generator_ollama.py
"""

import os
import subprocess
import time
import json
import ast
import logging
from pathlib import Path

# --- Configuration ---
PROJECT_ROOT = Path(".").resolve()
EXCLUDE_DIRS = {"venv", "__pycache__", "tests", "build", "dist", ".git", ".cursor"}
EXCLUDE_FILES = {"__init__.py"}
OLLAMA_MODEL = "deepseek-r1"
OLLAMA_CMD = f"ollama run {OLLAMA_MODEL}"
WAIT_TIMEOUT = 600
PAUSE_BETWEEN_FILES = 1
OUTPUT_DIR = Path("cursor_prompts/ollama_tests")
REPORT_FILE = OUTPUT_DIR / "test_generation_report.json"
SKIP_LIST_FILE = OUTPUT_DIR / "test_skip_list.json"
MAX_FAILURES = 2

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OllamaTestGen")

# --- Utility Functions ---
def is_test_file(file_path: Path) -> bool:
    return file_path.name.startswith("test_") or "test_" in file_path.name

def contains_testable_code(file_path: Path) -> bool:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        return any(isinstance(node, (ast.FunctionDef, ast.ClassDef)) for node in ast.walk(tree))
    except Exception as e:
        logger.error(f"AST parsing error for {file_path}: {e}")
        return False

def find_python_files() -> list:
    files = []
    for root, dirs, filenames in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in filenames:
            if fname.endswith(".py") and fname not in EXCLUDE_FILES:
                path = Path(root) / fname
                if not is_test_file(path) and contains_testable_code(path):
                    files.append(path.resolve())
    return files

def load_json_safe(path: Path, default=None):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            logger.warning(f"Corrupted JSON file {path}, resetting.")
    return default if default is not None else {}

def save_json_safe(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def call_ollama(prompt: str) -> str:
    try:
        result = subprocess.run(
            OLLAMA_CMD.split(),
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=WAIT_TIMEOUT
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except subprocess.TimeoutExpired:
        logger.error("Ollama call timed out.")
        return ""

def generate_test_prompt(file_path: Path) -> str:
    code = file_path.read_text(encoding="utf-8")
    return f"""Generate complete and runnable unittests using Python's unittest module for this code. Include edge cases and mock external dependencies. Return only the test code.

```python
{code}
```"""

def run_test_generation(file_path: Path) -> dict:
    prompt = generate_test_prompt(file_path)
    test_code = call_ollama(prompt)

    success = bool(test_code and "class" in test_code and "def test_" in test_code)
    test_file = OUTPUT_DIR / f"test_{file_path.stem}.py"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(test_file, "w", encoding="utf-8") as f:
        if success:
            f.write(test_code)
        else:
            f.write(
                "import unittest\n\n"
                "class PlaceholderTest(unittest.TestCase):\n"
                "    def test_placeholder(self):\n"
                "        self.assertTrue(True)\n\n"
                "if __name__ == '__main__':\n"
                "    unittest.main()\n"
            )

    return {"file": str(file_path), "success": success, "test_file": str(test_file)}

def run_unittest(test_file: Path) -> dict:
    cmd = ["python", "-m", "unittest", str(test_file)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=120)
        return {"success": result.returncode == 0, "output": result.stdout + result.stderr}
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "Timeout"}
    except Exception as e:
        return {"success": False, "output": str(e)}

def main():
    skip_list = load_json_safe(SKIP_LIST_FILE, {})
    files = find_python_files()
    logger.info(f"Found {len(files)} testable Python files.")

    results = []
    for file_path in files:
        file_str = str(file_path)
        if skip_list.get(file_str, 0) >= MAX_FAILURES:
            logger.info(f"Skipped {file_path} (repeated failures)")
            continue

        gen_res = run_test_generation(file_path)
        test_res = run_unittest(Path(gen_res["test_file"]))
        gen_res["unittest"] = test_res

        if not (gen_res["success"] and test_res["success"]):
            skip_list[file_str] = skip_list.get(file_str, 0) + 1
            logger.warning(f"❌ Failure in {file_path}")
        else:
            logger.info(f"✅ Success: {file_path}")

        results.append(gen_res)
        time.sleep(PAUSE_BETWEEN_FILES)

    save_json_safe(SKIP_LIST_FILE, skip_list)
    save_json_safe(REPORT_FILE, results)

    success_count = sum(r["success"] and r["unittest"]["success"] for r in results)
    fail_count = len(results) - success_count
    logger.info(f"✅ {success_count} passed, ❌ {fail_count} failed.")
    logger.info(f"Report saved: {REPORT_FILE}")

if __name__ == "__main__":
    main()
