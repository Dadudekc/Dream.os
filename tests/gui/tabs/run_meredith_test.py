#!/usr/bin/env python
"""
Run tests for the MeredithTab component.

This script sets up the Python path and runs the tests for the MeredithTab component.
"""

import os
import sys
import io
import pytest

# Fix Unicode encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

def run_meredith_test():
    """Run the MeredithTab tests with appropriate options."""
    print("Running MeredithTab tests...")

    # Define test arguments
    pytest_args = [
        # Test file
        os.path.join(os.path.dirname(__file__), 'test_meredith_tab.py'),

        # Verbose output
        "-v",

        # Show local variables in tracebacks
        "--showlocals",

        # Disable warnings
        "-p", "no:warnings",

        # Increase timeout for GUI tests
        "--timeout=60",
    ]

    # Run the tests
    print(f"Running pytest with arguments: {' '.join(pytest_args)}")
    return pytest.main(pytest_args)

if __name__ == "__main__":
    exit_code = run_meredith_test()
    sys.exit(exit_code) 