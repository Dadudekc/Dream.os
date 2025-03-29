#!/usr/bin/env python
"""
Run GUI tests for the PyQt5 application.

This script runs the PyQt5 GUI tests with appropriate options for pytest.
It ensures that the QApplication instance is properly created and that
all necessary fixtures are available.
"""

import os
import sys
import io
import pytest
import argparse

# Fix Unicode encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run PyQt5 GUI tests')
    parser.add_argument('--test', type=str, help='Run specific test file or test (e.g., test_main_tabs.py or test_main_tabs.py::test_init)')
    parser.add_argument('--no-html', action='store_true', help='Disable HTML report generation')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--list', action='store_true', help='List available tests without running them')
    return parser.parse_args()


def run_gui_tests():
    """Run the GUI tests with appropriate options."""
    print("Running PyQt5 GUI tests...")
    
    # Parse command line arguments
    args = parse_args()
    
    # List of test files
    test_files = [
        'test_main_tabs.py',
        'test_digital_dreamscape_tab.py',
        'test_prompt_execution_tab.py',
        'test_dreamscape_generation_tab.py',
        'test_community_management_tab.py',
        'test_analytics_tab.py',
        'test_settings_tab.py',
        'test_logs_tab.py',
        'test_historical_chats_tab.py',
        'test_configuration_tab.py'
    ]
    
    # If list option is enabled, just print the test files
    if args.list:
        print("Available test files:")
        for test_file in test_files:
            print(f"  {test_file}")
        return 0
    
    # Define test arguments
    pytest_args = [
        # Test discovery - either specific test or all tests
        args.test if args.test else os.path.dirname(__file__),
        
        # Verbose output
        "-v",
        
        # Show local variables in tracebacks
        "--showlocals",
        
        # Disable warnings
        "-p", "no:warnings",
        
        # Increase timeout for GUI tests
        "--timeout=60",
    ]
    
    # Add HTML report generation if not disabled
    if not args.no_html:
        pytest_args.extend([
            "--html=chat_mate/tests/gui/report.html",
            "--self-contained-html",
        ])
    
    # Add coverage if requested
    if args.coverage:
        pytest_args.extend([
            "--cov=chat_mate.gui",
            "--cov-report=term",
            "--cov-report=html:chat_mate/tests/gui/coverage",
        ])
    
    # Filter None and empty strings
    pytest_args = [arg for arg in pytest_args if arg]
    
    # Run the tests
    print(f"Running pytest with arguments: {' '.join(pytest_args)}")
    return pytest.main(pytest_args)


if __name__ == "__main__":
    exit_code = run_gui_tests()
    sys.exit(exit_code) 