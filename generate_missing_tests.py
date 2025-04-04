#!/usr/bin/env python3
"""
generate_missing_tests.py

Identifies modules and files without corresponding test files and generates them.
This helps ensure comprehensive test coverage across the codebase.

Usage:
    python generate_missing_tests.py [--auto-generate] [--module=<module_name>]
        [--run-tests] [--use-ollama] [--summary-only]
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime
import importlib.util
import inspect

# Configuration
PROJECT_ROOT = Path(".").resolve()
TEST_DIR = PROJECT_ROOT / "tests"
CACHE_PATH = PROJECT_ROOT / ".test_gen_cache.json"

def find_module_dirs(root=PROJECT_ROOT):
    """Find all Python packages (directories with __init__.py) excluding tests."""
    return [
        str(p.parent.relative_to(root))
        for p in root.glob("**/__init__.py")
        if "tests" not in str(p)
    ]

MODULE_DIRS = find_module_dirs()

def module_to_test_filename(module_path: Path) -> str:
    """Map a module filename to its corresponding test filename."""
    return f"test_{module_path.stem}.py"

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate tests for files without tests')
    parser.add_argument('--auto-generate', action='store_true',
                        help='Automatically generate test files for modules without tests')
    parser.add_argument('--module', type=str, help='Generate tests for a specific module only')
    parser.add_argument('--min-methods', type=int, default=1,
                        help='Minimum number of methods to consider a file for testing')
    parser.add_argument('--run-tests', action='store_true',
                        help='Run pytest on the generated tests')
    parser.add_argument('--use-ollama', action='store_true',
                        help='Use Ollama for test generation instead of templates')
    parser.add_argument('--summary-only', action='store_true',
                        help='Print summary of modules without tests but do not generate files')
    return parser.parse_args()

def load_cache():
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}

def save_cache(cache):
    CACHE_PATH.write_text(json.dumps(cache, indent=4), encoding='utf-8')

def find_python_modules():
    """Find all Python modules in the codebase."""
    modules = []
    for module_dir in MODULE_DIRS:
        module_path = PROJECT_ROOT / module_dir
        if not module_path.exists():
            continue
        for root, _, filenames in os.walk(module_path):
            for filename in filenames:
                if filename.endswith('.py') and not filename.startswith('__'):
                    file_path = Path(root) / filename
                    rel_path = file_path.relative_to(PROJECT_ROOT)
                    module_name = str(rel_path).replace(os.sep, ".")[:-3]
                    modules.append({
                        'path': file_path,
                        'relative_path': rel_path,
                        'name': module_name
                    })
    return modules

def find_existing_tests():
    """Find all existing test files."""
    tests = {}
    if not TEST_DIR.exists():
        return tests
    for root, _, filenames in os.walk(TEST_DIR):
        for filename in filenames:
            if filename.startswith('test_') and filename.endswith('.py'):
                test_path = Path(root) / filename
                tests[filename] = test_path
    return tests

def analyze_module_content(module_path):
    """Analyze module content to determine if it needs tests."""
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        spec = importlib.util.spec_from_file_location("module.name", module_path)
        if spec is None or spec.loader is None:
            return {'classes': [], 'functions': [], 'needs_test': False}
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            classes = []
            functions = []
            for name, obj in inspect.getmembers(module):
                if name.startswith('_'):
                    continue
                if inspect.isclass(obj) and obj.__module__ == module.__name__:
                    methods = [m for m, _ in inspect.getmembers(obj, inspect.isfunction) if not m.startswith('_')]
                    if methods:
                        classes.append({'name': name, 'methods': methods})
                elif inspect.isfunction(obj) and obj.__module__ == module.__name__:
                    functions.append(name)
            needs_test = bool(classes or functions)
            return {
                'classes': classes,
                'functions': functions,
                'needs_test': needs_test
            }
        except Exception as e:
            has_class = 'class ' in content
            has_function = 'def ' in content and not content.strip().startswith('def test_')
            return {
                'classes': [{'name': 'Unknown', 'methods': []}] if has_class else [],
                'functions': ['unknown_function'] if has_function else [],
                'needs_test': has_class or has_function,
                'import_error': str(e)
            }
    except Exception as e:
        return {
            'error': str(e),
            'needs_test': False
        }

def generate_test_template(module_info):
    """
    Generate a test file template for a module using unittest and pytest.
    
    This function builds a test class named based on the module's last part.
    It creates placeholder test methods for each public class method and function.
    """
    module_path = module_info['path']
    module_name = module_info['name']
    # Read module source if needed (currently unused)
    with open(module_path, 'r', encoding='utf-8') as f:
        _ = f.read()

    # Generate import statement based on module name.
    if module_name.startswith('chat_mate.'):
        import_stmt = f"from {module_name} import *"
    else:
        import_stmt = f"import {module_name}"

    test_content = f"""import unittest
import pytest
from unittest.mock import Mock, patch, MagicMock
{import_stmt}

class Test{module_name.split('.')[-1].capitalize()}(unittest.TestCase):
    \"\"\"Tests for {module_name} module.\"\"\"
    
    def setUp(self):
        \"\"\"Set up test fixtures, if any.\"\"\"
        pass

    def tearDown(self):
        \"\"\"Tear down test fixtures, if any.\"\"\"
        pass
"""
    # Add test methods for each class in the module.
    for cls in module_info['content'].get('classes', []):
        cls_name = cls['name']
        for method in cls['methods']:
            test_content += f"""
    def test_{method}_should_work(self):
        \"\"\"Test that {cls_name}.{method} works as expected.\"\"\"
        # TODO: Implement test for {cls_name}.{method}
        self.assertTrue(True)
"""
    # Add parametrized test methods for each function in the module.
    for func in module_info['content'].get('functions', []):
        test_content += f"""
    @pytest.mark.parametrize("input_value,expected", [
        (None, None),  # TODO: Add real test cases for {func}
    ])
    def test_{func}_parametrized(self, input_value, expected):
        \"\"\"Test {func} with multiple scenarios.\"\"\"
        result = {func}(input_value)
        assert result == expected
"""
    # Fallback: if no classes or functions found, add a simple existence test.
    if not module_info['content'].get('classes') and not module_info['content'].get('functions'):
        test_content += """
    def test_module_exists(self):
        \"\"\"Test that the module exists.\"\"\"
        self.assertTrue(True)
"""
    test_content += """
if __name__ == '__main__':
    unittest.main()
"""
    return test_content

def generate_test_with_ollama(module_path):
    """Generate a test file using Ollama."""
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        ollama_cmd = "ollama run deepseek-r1"
        prompt = f"""Generate a comprehensive pytest test file for this Python module.
Include tests for all public methods and functions with appropriate mocks and fixtures.
Focus on edge cases and error conditions. Return ONLY the complete test code.

```python
{source_code}
```"""
        cmd = ollama_cmd.split()
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600
        )
        output = result.stdout.strip()
        if "```python" in output and "```" in output:
            start = output.find("```python") + len("```python")
            end = output.rfind("```")
            if start < end:
                code = output[start:end].strip()
                return code
        return output
    except subprocess.TimeoutExpired:
        return "# Error: Ollama call timed out."
    except Exception as e:
        return f"# Error generating test: {str(e)}"

def format_with_black(file_path: Path):
    """Run Black to format the given file."""
    try:
        subprocess.run(["black", str(file_path)], stdout=subprocess.DEVNULL, check=True)
    except Exception as e:
        print(f"Warning: Black formatting failed for {file_path}: {e}")

def create_test_file(module_info, use_ollama=False):
    """Create a test file for a module and format it."""
    module_path = module_info['path']
    test_filename = module_to_test_filename(module_path)
    # Create test directory matching module's subdirectory structure if needed.
    if module_info['relative_path'].parts[0] == "chat_mate":
        subdir = Path(*module_info['relative_path'].parts[1:-1])
        test_dir = TEST_DIR / subdir
    else:
        test_dir = TEST_DIR
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_dir / test_filename

    # Use cache to avoid regenerating tests too often.
    cache = load_cache()
    last_gen = cache.get(module_info['name'], {}).get("generated_at")
    regenerate = True
    if last_gen:
        last_time = datetime.fromisoformat(last_gen)
        delta = datetime.utcnow() - last_time
        if delta.total_seconds() < 300:
            regenerate = False
            print(f"Skipping regeneration for {module_info['name']} (generated {delta.total_seconds():.0f}s ago)")

    if regenerate:
        if use_ollama:
            test_content = generate_test_with_ollama(module_path)
        else:
            test_content = generate_test_template(module_info)
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        format_with_black(test_file)
        # Update cache.
        cache[module_info['name']] = {
            "file": str(test_file),
            "generated_at": datetime.utcnow().isoformat()
        }
        save_cache(cache)
        print(f"Created {test_file}")
    else:
        print(f"Test file already up-to-date: {test_file}")

    return test_file

def run_tests(test_files):
    """Run pytest on the generated test files."""
    if not test_files:
        return
    print(f"\nRunning tests on {len(test_files)} generated test file(s)...")
    cmd = ["pytest", "-v"] + [str(f) for f in test_files]
    subprocess.run(cmd, cwd=str(PROJECT_ROOT))

def main():
    args = parse_args()
    print("Finding Python modules...")
    modules = find_python_modules()
    print("Finding existing tests...")
    existing_tests = find_existing_tests()

    modules_without_tests = []
    print("\nAnalyzing modules for testability...")
    for module in modules:
        # Use consistent mapping from module path to test file name.
        test_filename = module_to_test_filename(module['path'])
        if test_filename in existing_tests:
            continue
        if args.module and not module['name'].startswith(args.module):
            continue
        content = analyze_module_content(module['path'])
        total_methods = sum(len(cls.get('methods', [])) for cls in content.get('classes', []))
        total_methods += len(content.get('functions', []))
        if content.get('needs_test', False) and total_methods >= args.min_methods:
            module['content'] = content
            module['total_methods'] = total_methods
            modules_without_tests.append(module)

    print(f"\nFound {len(modules_without_tests)} modules without tests:")
    for i, module in enumerate(modules_without_tests, 1):
        print(f"{i}. {module['name']} ({module['total_methods']} testable methods)")

    if args.summary_only:
        return 0

    generated_files = []
    if args.auto_generate:
        print("\nGenerating test files...")
        for module in modules_without_tests:
            test_file = create_test_file(module, use_ollama=args.use_ollama)
            generated_files.append(test_file)
    else:
        print("\nTo generate test files, run with --auto-generate flag")

    if args.run_tests and generated_files:
        run_tests(generated_files)

    return 0

if __name__ == "__main__":
    sys.exit(main())
