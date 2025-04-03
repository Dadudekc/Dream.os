"""Test runner for dream modules.

This script runs all module checks and generates a detailed report
of test results, including timing information and error details.
"""
import os
import sys
import time
import logging
import traceback
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

# Import check modules script
from .check_modules import (
    setup_test_dirs,
    check_character_model,
    check_clan_model,
    check_character_manager,
    check_clan_manager,
    check_service_container
)


@dataclass
class TestResult:
    """Container for test results."""
    name: str
    passed: bool
    duration: float
    error: str = ""
    details: Dict[str, Any] = None


class TestRunner:
    """Test runner for dream modules."""
    
    def __init__(self):
        """Initialize the test runner."""
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up logging configuration."""
        # Create logs directory
        os.makedirs("logs", exist_ok=True)
        
        # Create handlers
        console_handler = logging.StreamHandler(sys.stdout)
        file_handler = logging.FileHandler(
            f"logs/test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        
        # Set formats
        console_format = logging.Formatter('%(levelname)s: %(message)s')
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        console_handler.setFormatter(console_format)
        file_handler.setFormatter(file_format)
        
        # Add handlers to logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.INFO)
    
    def run_test(self, test_func: callable, test_name: str) -> TestResult:
        """Run a single test function.
        
        Args:
            test_func: The test function to run
            test_name: Name of the test
            
        Returns:
            TestResult object containing test results
        """
        self.logger.info(f"Running test: {test_name}")
        start_time = time.time()
        
        try:
            test_func()
            duration = time.time() - start_time
            result = TestResult(
                name=test_name,
                passed=True,
                duration=duration
            )
            self.logger.info(f"Test passed: {test_name} ({duration:.2f}s)")
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"{type(e).__name__}: {str(e)}"
            result = TestResult(
                name=test_name,
                passed=False,
                duration=duration,
                error=error_msg,
                details={"traceback": traceback.format_exc()}
            )
            self.logger.error(f"Test failed: {test_name}")
            self.logger.error(f"Error: {error_msg}")
            self.logger.debug(traceback.format_exc())
        
        self.results.append(result)
        return result
    
    def run_all_tests(self):
        """Run all module tests."""
        self.start_time = time.time()
        self.logger.info("Starting test run...")
        
        # Test functions to run
        tests = [
            (setup_test_dirs, "Test Directory Setup"),
            (check_character_model, "Character Model"),
            (check_clan_model, "Clan Model"),
            (check_character_manager, "Character Manager"),
            (check_clan_manager, "Clan Manager"),
            (check_service_container, "Service Container")
        ]
        
        # Run each test
        for test_func, test_name in tests:
            self.run_test(test_func, test_name)
        
        self.end_time = time.time()
        self.logger.info("Test run complete")
    
    def generate_report(self) -> str:
        """Generate a detailed test report.
        
        Returns:
            Test report as a string
        """
        total_time = self.end_time - self.start_time
        passed_tests = sum(1 for r in self.results if r.passed)
        total_tests = len(self.results)
        
        report = [
            "Dream Modules Test Report",
            "=" * 50,
            f"Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Time: {total_time:.2f}s",
            f"Tests Passed: {passed_tests}/{total_tests}",
            "=" * 50,
            "\nTest Results:",
            "-" * 50
        ]
        
        # Add individual test results
        for result in self.results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            report.append(f"\n{result.name}:")
            report.append(f"Status: {status}")
            report.append(f"Duration: {result.duration:.2f}s")
            
            if not result.passed:
                report.append(f"Error: {result.error}")
                if result.details and "traceback" in result.details:
                    report.append("\nTraceback:")
                    report.append(result.details["traceback"])
            
            report.append("-" * 50)
        
        return "\n".join(report)
    
    def save_report(self, report: str):
        """Save the test report to a file.
        
        Args:
            report: The test report string
        """
        # Create reports directory
        os.makedirs("reports", exist_ok=True)
        
        # Save report
        filename = f"reports/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        
        self.logger.info(f"Test report saved to {filename}")
    
    def cleanup(self):
        """Clean up test data and artifacts."""
        try:
            # Remove test directories and their contents
            import shutil
            if os.path.exists("test_data"):
                shutil.rmtree("test_data")
            
            self.logger.info("Test cleanup complete")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


def main():
    """Run the test suite."""
    runner = TestRunner()
    
    try:
        # Run all tests
        runner.run_all_tests()
        
        # Generate and save report
        report = runner.generate_report()
        runner.save_report(report)
        
        # Print report to console
        print("\n" + report)
        
        # Clean up
        runner.cleanup()
        
        # Exit with appropriate code
        sys.exit(0 if all(r.passed for r in runner.results) else 1)
        
    except Exception as e:
        runner.logger.error(f"Error running tests: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main() 