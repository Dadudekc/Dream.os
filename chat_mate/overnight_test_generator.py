#!/usr/bin/env python3
"""
overnight_test_generator.py

Automates overnight generation and execution of Python unittests using Ollama's deepseek-r1 model.
Now includes code coverage analysis and reporting.

Improvements:
- Explicit UTF-8 encoding for all file operations.
- AST filtering ensures only testable files (containing classes/functions) are processed.
- Robust error handling and logging.
- Maintains skip list to avoid redundant processing.
- Generates comprehensive JSON reports.
- Collects and reports code coverage metrics.

Usage:
    python overnight_test_generator.py
"""

import os
import subprocess
import time
import json
import ast
import logging
import sys
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
COVERAGE_DIR = PROJECT_ROOT / "reports" / "coverage"
MIN_COVERAGE = 70
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

def get_missing_coverage_files() -> list:
    """Identifies Python files that have low or no test coverage."""
    # Ensure the coverage directory exists
    COVERAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # Run a coverage analysis on all tests
        cmd = [
            "pytest", 
            "--cov=chat_mate", 
            "--cov-report", f"html:{COVERAGE_DIR}",
            "--cov-report", "term",
            "tests/"
        ]
        subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True)
        
        # Parse the coverage data
        cov_cmd = ["coverage", "json", "-o", str(COVERAGE_DIR / "coverage.json")]
        subprocess.run(cov_cmd, cwd=str(PROJECT_ROOT))
        
        # Read the coverage JSON
        with open(COVERAGE_DIR / "coverage.json", "r", encoding="utf-8") as f:
            cov_data = json.load(f)
        
        missing_files = []
        for file_path, data in cov_data.get("files", {}).items():
            coverage = data.get("summary", {}).get("percent_covered", 0)
            if coverage < MIN_COVERAGE:
                missing_files.append(Path(file_path))
        
        return missing_files
    except Exception as e:
        logger.error(f"Error analyzing coverage: {e}")
        return []

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
    return f"""Generate complete and runnable unittests using Python's unittest module for this code. Include edge cases and mock external dependencies. Focus on achieving high code coverage. Return only the test code.

```python
{code}
```"""

def generate_coverage_improved_test_prompt(file_path: Path, missing_lines: list) -> str:
    code = file_path.read_text(encoding="utf-8")
    return f"""Generate additional unittests for this code to increase coverage. Specifically focus on the following uncovered line numbers: {', '.join(map(str, missing_lines))}. Include edge cases and mock external dependencies as needed. Return only the test code that can be appended to an existing test file.

```python
{code}
```"""

def run_test_generation(file_path: Path, missing_lines=None) -> dict:
    if missing_lines:
        prompt = generate_coverage_improved_test_prompt(file_path, missing_lines)
    else:
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

def run_coverage_on_file(file_path: Path, test_file: Path) -> dict:
    """Run pytest with coverage on a specific file and its test."""
    try:
        cmd = [
            "pytest", 
            "--cov=" + str(file_path.parent), 
            str(test_file)
        ]
        result = subprocess.run(
            cmd, 
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120
        )
        
        # Get coverage data for this specific file
        cov_cmd = ["coverage", "report", "-m", str(file_path)]
        cov_result = subprocess.run(
            cov_cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True, 
            text=True,
            encoding="utf-8"
        )
        
        # Extract coverage percentage and missing lines
        lines = cov_result.stdout.strip().split('\n')
        coverage_data = {}
        
        if len(lines) >= 2:
            parts = lines[-1].split()
            if len(parts) >= 5:
                try:
                    coverage_data["percent"] = float(parts[-3].strip('%'))
                    missing = parts[-1]
                    if missing != "":
                        coverage_data["missing_lines"] = [int(x.strip()) for x in missing.split(',') if x.strip().isdigit()]
                    else:
                        coverage_data["missing_lines"] = []
                except (ValueError, IndexError):
                    coverage_data["percent"] = 0
                    coverage_data["missing_lines"] = []
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout + result.stderr,
            "coverage": coverage_data
        }
    except Exception as e:
        logger.error(f"Coverage error for {file_path}: {e}")
        return {"success": False, "output": str(e), "coverage": {"percent": 0, "missing_lines": []}}

def main():
    skip_list = load_json_safe(SKIP_LIST_FILE, {})
    
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--coverage-only":
        logger.info("Running in coverage-only mode to find and fix missing coverage.")
        missing_coverage_files = get_missing_coverage_files()
        if not missing_coverage_files:
            logger.info("No files with insufficient coverage found.")
            return
        
        logger.info(f"Found {len(missing_coverage_files)} files with less than {MIN_COVERAGE}% coverage.")
        files = missing_coverage_files
    else:
        files = find_python_files()
        logger.info(f"Found {len(files)} testable Python files.")

    results = []
    for file_path in files:
        file_str = str(file_path)
        if skip_list.get(file_str, 0) >= MAX_FAILURES:
            logger.info(f"Skipped {file_path} (repeated failures)")
            continue

        logger.info(f"Processing {file_path}")
        
        # First generate basic tests for the file
        gen_res = run_test_generation(file_path)
        test_res = run_unittest(Path(gen_res["test_file"]))
        gen_res["unittest"] = test_res
        
        # If the basic test was successful, check coverage
        if gen_res["success"] and test_res["success"]:
            logger.info(f"Running coverage analysis for {file_path}")
            cov_res = run_coverage_on_file(file_path, Path(gen_res["test_file"]))
            gen_res["coverage"] = cov_res["coverage"]
            
            # If coverage is below threshold, try to improve it
            if cov_res["coverage"]["percent"] < MIN_COVERAGE and cov_res["coverage"]["missing_lines"]:
                logger.info(f"Coverage is {cov_res['coverage']['percent']}%, attempting to improve...")
                
                # Try to generate additional tests to improve coverage
                improved_gen_res = run_test_generation(
                    file_path, 
                    missing_lines=cov_res["coverage"]["missing_lines"]
                )
                
                # If successful, append to existing test file
                if improved_gen_res["success"]:
                    with open(gen_res["test_file"], "a", encoding="utf-8") as f:
                        additional_code = Path(improved_gen_res["test_file"]).read_text(encoding="utf-8")
                        f.write("\n\n# Additional tests to improve coverage\n")
                        # Remove duplicate imports, classes, and main block
                        lines = additional_code.split('\n')
                        in_imports = True
                        for line in lines:
                            if not line.strip():
                                in_imports = False
                            if (not in_imports and 
                                not line.startswith("import ") and 
                                not line.startswith("from ") and
                                "if __name__ == '__main__'" not in line and
                                "unittest.main()" not in line):
                                f.write(line + "\n")
                    
                    # Re-run tests and coverage
                    test_res = run_unittest(Path(gen_res["test_file"]))
                    gen_res["unittest"] = test_res
                    cov_res = run_coverage_on_file(file_path, Path(gen_res["test_file"]))
                    gen_res["coverage"] = cov_res["coverage"]
                    gen_res["coverage_improved"] = cov_res["coverage"]["percent"]
        
        if not (gen_res["success"] and test_res["success"]):
            skip_list[file_str] = skip_list.get(file_str, 0) + 1
            logger.warning(f"❌ Failure in {file_path}")
        else:
            coverage_percent = gen_res.get("coverage", {}).get("percent", 0)
            logger.info(f"✅ Success: {file_path} (Coverage: {coverage_percent}%)")

        results.append(gen_res)
        time.sleep(PAUSE_BETWEEN_FILES)

    save_json_safe(SKIP_LIST_FILE, skip_list)
    save_json_safe(REPORT_FILE, results)

    success_count = sum(r["success"] and r["unittest"]["success"] for r in results)
    fail_count = len(results) - success_count
    logger.info(f"✅ {success_count} passed, ❌ {fail_count} failed.")
    
    # Calculate overall coverage
    total_coverage = sum(r.get("coverage", {}).get("percent", 0) for r in results if r["success"] and r["unittest"]["success"])
    avg_coverage = total_coverage / success_count if success_count > 0 else 0
    logger.info(f"Average coverage: {avg_coverage:.2f}%")
    
    logger.info(f"Report saved: {REPORT_FILE}")
    
    # Create consolidated coverage report
    try:
        logger.info("Generating consolidated coverage report...")
        cmd = [
            "pytest", 
            "--cov=chat_mate", 
            "--cov-report", f"html:{COVERAGE_DIR}",
            "tests/"
        ]
        subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        logger.info(f"Consolidated coverage report saved to {COVERAGE_DIR}")
    except Exception as e:
        logger.error(f"Error generating consolidated report: {e}")

if __name__ == "__main__":
    main()
