#!/usr/bin/env python3
"""
generate_missing_tests.py

Identifies modules and files without corresponding test files and generates them.
This helps ensure comprehensive test coverage across the codebase.

Usage:
    python generate_missing_tests.py [--auto-generate] [--module=<module_name>]
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
import importlib.util
import inspect

# Configuration
PROJECT_ROOT = Path(".").resolve()
TEST_DIR = PROJECT_ROOT / "tests"
MODULE_DIRS = ["chat_mate"]  # Add other module directories if needed

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
    return parser.parse_args()

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
                    
                    module_name = str(rel_path).replace('/', '.').replace('\\', '.')[:-3]
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
                module_name = filename[5:-3]  # Remove 'test_' prefix and '.py' suffix
                tests[module_name] = test_path
    
    return tests

def analyze_module_content(module_path):
    """Analyze module content to determine if it needs tests."""
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Try to load the module to inspect its contents
        spec = importlib.util.spec_from_file_location("module.name", module_path)
        if spec is None or spec.loader is None:
            return {'classes': [], 'functions': [], 'needs_test': False}
            
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            
            # Find classes and functions
            classes = []
            functions = []
            
            for name, obj in inspect.getmembers(module):
                if name.startswith('_'):
                    continue
                    
                if inspect.isclass(obj) and obj.__module__ == module.__name__:
                    methods = []
                    for method_name, method in inspect.getmembers(obj, inspect.isfunction):
                        if not method_name.startswith('_'):
                            methods.append(method_name)
                    
                    if methods:  # Only include classes with methods
                        classes.append({'name': name, 'methods': methods})
                        
                elif inspect.isfunction(obj) and obj.__module__ == module.__name__:
                    functions.append(name)
            
            # Determine if the module needs tests
            needs_test = bool(classes or functions)
            
            return {
                'classes': classes,
                'functions': functions,
                'needs_test': needs_test
            }
        except Exception as e:
            # Fallback to simple check if import fails
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
    """Generate a test file template for a module."""
    module_path = module_info['path']
    module_name = module_info['name']
    content = module_info['content']
    
    with open(module_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # Generate appropriate import statement for the module
    if module_name.startswith('chat_mate.'):
        import_stmt = f"from {module_name} import *"
    else:
        import_stmt = f"import {module_name}"
    
    # Start building the test file content
    test_content = f"""import unittest
import pytest
from unittest.mock import Mock, patch, MagicMock
{import_stmt}

class Test{module_name.split('.')[-1].capitalize()}(unittest.TestCase):
    \"\"\"
    Tests for {module_name} module.
    \"\"\"
    
    def setUp(self):
        \"\"\"Set up test fixtures, if any.\"\"\"
        pass
    
    def tearDown(self):
        \"\"\"Tear down test fixtures, if any.\"\"\"
        pass
"""
    
    # Add test methods for each class
    for cls in content['classes']:
        cls_name = cls['name']
        for method in cls['methods']:
            test_content += f"""
    def test_{method}_should_work(self):
        \"\"\"Test that {cls_name}.{method} works as expected.\"\"\"
        # TODO: Implement test for {cls_name}.{method}
        self.assertTrue(True)  # Placeholder assertion
"""
    
    # Add test methods for each function
    for func in content['functions']:
        test_content += f"""
    def test_{func}_should_work(self):
        \"\"\"Test that {func} function works as expected.\"\"\"
        # TODO: Implement test for {func} function
        self.assertTrue(True)  # Placeholder assertion
"""
    
    # Add a simple placeholder test if no classes or functions were found
    if not content['classes'] and not content['functions']:
        test_content += """
    def test_module_exists(self):
        \"\"\"Test that the module exists.\"\"\"
        self.assertTrue(True)
"""
    
    # Add main block
    test_content += """
if __name__ == '__main__':
    unittest.main()
"""
    
    return test_content

def generate_test_with_ollama(module_path):
    """Generate test file using Ollama."""
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        ollama_cmd = "ollama run deepseek-r1"
        prompt = f"""Generate a comprehensive pytest test file for this Python module. Include tests for all public methods and functions with appropriate mocks and fixtures. Focus on edge cases and error conditions. Make the tests clear, maintainable, and following good testing practices.

```python
{source_code}
```

Return ONLY the complete test code that I could save directly to a test file."""
        
        cmd = ollama_cmd.split()
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600  # 10 minute timeout
        )
        
        # Process the output to extract just the code
        output = result.stdout.strip()
        
        # Look for code block markers and extract content between them
        if "```python" in output and "```" in output:
            start = output.find("```python") + 10
            end = output.rfind("```")
            if start > 10 and end > start:
                code = output[start:end].strip()
                return code
        
        # If we can't find clearly marked code blocks, return the raw output
        return output
    except subprocess.TimeoutExpired:
        return "# Error: Ollama call timed out."
    except Exception as e:
        return f"# Error generating test: {str(e)}"

def create_test_file(module_info, use_ollama=False):
    """Create a test file for a module."""
    module_path = module_info['path']
    module_name = module_info['relative_path'].stem
    
    # Determine the test file path
    if module_info['relative_path'].parts[0] == "chat_mate":
        # Put tests in a directory structure matching the module
        subdir = Path(*module_info['relative_path'].parts[1:-1])
        test_dir = TEST_DIR / subdir
    else:
        test_dir = TEST_DIR
    
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_dir / f"test_{module_name}.py"
    
    # Generate test content
    if use_ollama:
        test_content = generate_test_with_ollama(module_path)
    else:
        test_content = generate_test_template(module_info)
    
    # Write the test file
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    return test_file

def run_tests(test_files):
    """Run pytest on the generated test files."""
    if not test_files:
        return
        
    print(f"\nRunning tests on {len(test_files)} newly generated test files...")
    
    cmd = ["pytest", "-v"] + [str(f) for f in test_files]
    subprocess.run(cmd, cwd=str(PROJECT_ROOT))

def main():
    """Main entry point."""
    args = parse_args()
    
    print("Finding Python modules...")
    modules = find_python_modules()
    
    print("Finding existing tests...")
    existing_tests = find_existing_tests()
    
    modules_without_tests = []
    
    print("\nAnalyzing modules for testability...")
    for module in modules:
        module_name = module['path'].stem
        
        # Skip if tests already exist for this module
        if module_name in existing_tests:
            continue
            
        # Skip if module-specific and this isn't the requested module
        if args.module and not module['name'].startswith(args.module):
            continue
            
        # Analyze the module content
        content = analyze_module_content(module['path'])
        
        # Only include modules with methods that need tests
        total_methods = sum(len(cls.get('methods', [])) for cls in content.get('classes', []))
        total_methods += len(content.get('functions', []))
        
        if content.get('needs_test', False) and total_methods >= args.min_methods:
            module['content'] = content
            module['total_methods'] = total_methods
            modules_without_tests.append(module)
    
    print(f"\nFound {len(modules_without_tests)} modules without tests:")
    for i, module in enumerate(modules_without_tests, 1):
        print(f"{i}. {module['name']} ({module['total_methods']} testable methods)")
    
    generated_files = []
    
    if args.auto_generate:
        print("\nGenerating test files...")
        for module in modules_without_tests:
            print(f"Generating tests for {module['name']}...")
            test_file = create_test_file(module, use_ollama=args.use_ollama)
            print(f"Created {test_file}")
            generated_files.append(test_file)
    else:
        print("\nTo generate test files, run with --auto-generate flag")
        
    if args.run_tests and generated_files:
        run_tests(generated_files)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 