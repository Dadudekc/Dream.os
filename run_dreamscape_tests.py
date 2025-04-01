#!/usr/bin/env python3
"""
Dreamscape Tab Test Runner

This script runs all tests for the Dreamscape tab component.
It can run with or without coverage reporting.

Usage:
    python run_dreamscape_tests.py [--coverage]
"""

import os
import sys
import pytest
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dreamscape_tests.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("dreamscape_tests")

def run_tests():
    """Run all tests for the Dreamscape tab."""
    logger.info("Starting Dreamscape tab tests...")
    
    # Get the directory of this script
    current_dir = Path(__file__).parent
    
    # Run tests with specific arguments
    result = pytest.main([
        "-v",                  # Verbose output
        "--no-header",         # Skip pytest header
        "--tb=short",          # Short traceback format
        "--no-summary",        # Skip test summary
        "--exitfirst",         # Stop on first failure
        str(current_dir)       # Run tests in the current directory
    ])
    
    # Log result
    if result == 0:
        logger.info("All tests passed successfully!")
    else:
        logger.error(f"Tests failed with exit code: {result}")
    
    return result

def run_tests_with_coverage():
    """Run tests with coverage reporting."""
    logger.info("Starting Dreamscape tab tests with coverage...")
    
    # Get the directory of this script
    current_dir = Path(__file__).parent
    
    # Run tests with coverage
    result = pytest.main([
        "-v",                  # Verbose output
        "--no-header",         # Skip pytest header
        "--tb=short",          # Short traceback format
        "--no-summary",        # Skip test summary
        "--exitfirst",         # Stop on first failure
        "--cov=interfaces.pyqt.tabs.dreamscape_generation",  # Coverage target
        "--cov-report=term",   # Terminal report
        "--cov-report=html:coverage_html",  # HTML report
        str(current_dir)       # Run tests in the current directory
    ])
    
    # Log result
    if result == 0:
        logger.info("All tests passed successfully with coverage!")
    else:
        logger.error(f"Tests failed with exit code: {result}")
    
    return result

if __name__ == "__main__":
    # Check for coverage argument
    if len(sys.argv) > 1 and sys.argv[1] == "--coverage":
        result = run_tests_with_coverage()
    else:
        result = run_tests()
    
    # Exit with the test result code
    sys.exit(result) 
