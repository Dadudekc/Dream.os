import unittest
import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import test modules
from tests.integration.test_community_integration import TestCommunityIntegration
from tests.test_community_scheduler import TestCommunityScheduler

def run_async_tests(test_class):
    """Run async test cases."""
    loop = asyncio.get_event_loop()
    
    # Get all test methods
    test_methods = [m for m in dir(test_class) if m.startswith('test_')]
    suite = unittest.TestSuite()
    
    for method in test_methods:
        test_case = test_class(method)
        if asyncio.iscoroutinefunction(getattr(test_class, method)):
            # Wrap async test in sync wrapper
            def wrapper(test_case, method):
                def run_async():
                    loop.run_until_complete(getattr(test_case, method)())
                return run_async
            setattr(test_case, method, wrapper(test_case, method))
        suite.addTest(test_case)
    
    return suite

def main():
    """Run all tests."""
    # Ensure data directory exists
    os.makedirs(os.getenv("DATA_DIR", "./data"), exist_ok=True)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add async tests
    suite.addTests(run_async_tests(TestCommunityIntegration))
    
    # Add sync tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCommunityScheduler))
    
    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(not result.wasSuccessful())

if __name__ == '__main__':
    main() 