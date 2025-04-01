"""
Test Runner Service

This service handles test execution and reporting for the application.
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class TestRunner:
    """Service for running tests and managing test results."""
    
    def __init__(self, project_root: str = '.'):
        """
        Initialize the test runner.
        
        Args:
            project_root: Path to the project root directory
        """
        self.project_root = Path(project_root)
        self.logger = logger
        
    def run_tests(self, test_path: Optional[str] = None, pattern: str = "test_*.py") -> Dict[str, Any]:
        """
        Run tests in the specified path or all tests if no path provided.
        
        Args:
            test_path: Optional specific test file or directory to run
            pattern: Pattern to match test files
            
        Returns:
            Dictionary containing test results
        """
        try:
            cmd = ["python", "-m", "pytest"]
            
            if test_path:
                cmd.append(str(Path(test_path)))
            else:
                cmd.extend([str(self.project_root / "tests"), "-v"])
                
            cmd.extend(["-k", pattern])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
                "return_code": result.returncode
            }
            
        except Exception as e:
            self.logger.error(f"Error running tests: {e}")
            return {
                "success": False,
                "output": "",
                "errors": str(e),
                "return_code": -1
            }
    
    def run_specific_test(self, test_file: str, test_name: str) -> Dict[str, Any]:
        """
        Run a specific test by name.
        
        Args:
            test_file: Path to the test file
            test_name: Name of the test to run
            
        Returns:
            Dictionary containing test results
        """
        return self.run_tests(test_file, pattern=test_name)
    
    def get_test_coverage(self) -> Dict[str, Any]:
        """
        Get test coverage information.
        
        Returns:
            Dictionary containing coverage metrics
        """
        try:
            cmd = ["python", "-m", "pytest", "--cov=.", "--cov-report=term-missing"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            return {
                "success": result.returncode == 0,
                "coverage_output": result.stdout,
                "errors": result.stderr
            }
            
        except Exception as e:
            self.logger.error(f"Error getting test coverage: {e}")
            return {
                "success": False,
                "coverage_output": "",
                "errors": str(e)
            } 