#!/usr/bin/env python
import sys
import pytest
import logging
from pathlib import Path
import os

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.absolute())
sys.path.insert(0, project_root)

# Configure logging
log_file = os.path.join(project_root, "test_run.log")
if os.path.exists(log_file):
    os.remove(log_file)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_tests():
    try:
        logger.info("Starting test run...")
        
        # Set up test arguments
        test_args = [
            'tests/unit',
            'tests/integration',
            '--verbose',
            '--capture=no',
            '--tb=short',
            '-p', 'no:warnings',
            '--asyncio-mode=auto',
            '--durations=10',
            '--showlocals',
            '-v',
            '--cov=interfaces',
            '--cov-report=term-missing',
            '--cov-report=html:coverage_report'
        ]
        
        logger.info("Coverage reporting enabled")
        logger.info(f"Running tests with arguments: {test_args}")
        
        import pytest
        exit_code = pytest.main(test_args)
        
        if exit_code != 0:
            logger.error(f"Test run failed with exit code: {exit_code}")
        else:
            logger.info("Test run completed successfully")
            
        return exit_code
        
    except Exception as e:
        logger.error(f"Error running tests: {str(e)}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(run_tests()) 
