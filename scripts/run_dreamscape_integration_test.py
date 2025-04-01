#!/usr/bin/env python3
"""
Run Dreamscape Integration Test Script

This script provides a convenient way to run the Dreamscape integration test
that verifies the proper functioning of the context synthesizer and dreamscape
generation service integration.
"""

import os
import sys
import unittest
import logging
from pathlib import Path

# Add the project root to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def run_tests():
    """Run the dreamscape integration tests."""
    logger.info("Starting Dreamscape integration tests...")
    
    try:
        # Import the test module
        from tests.test_dreamscape_integration import TestDreamscapeIntegration
        
        # Create a test suite with our test class
        test_suite = unittest.TestLoader().loadTestsFromTestCase(TestDreamscapeIntegration)
        
        # Run the tests
        test_runner = unittest.TextTestRunner(verbosity=2)
        result = test_runner.run(test_suite)
        
        # Log the results
        logger.info(f"Tests run: {result.testsRun}")
        logger.info(f"Errors: {len(result.errors)}")
        logger.info(f"Failures: {len(result.failures)}")
        
        if result.wasSuccessful():
            logger.info("All tests passed!")
            return 0
        else:
            logger.error("Some tests failed!")
            return 1
            
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests()) 
