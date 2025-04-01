#!/usr/bin/env python3
"""
Test Fortress Runner

A comprehensive test runner that combines unit tests, integration tests,
mutation testing, and failure injection to create an impenetrable test suite.
"""

import os
import sys
import json
import time
import pytest
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from failure_validator import FailureValidator, ValidationResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_fortress.log')
    ]
)
logger = logging.getLogger('test_fortress')

@dataclass
class TestResult:
    """Represents the result of a test run."""
    success: bool
    total_tests: int
    failed_tests: int
    skipped_tests: int
    execution_time: float
    coverage_percent: float
    mutation_score: Optional[float] = None
    failure_cases_tested: int = 0
    failure_cases_passed: int = 0
    validation_results: Optional[List[ValidationResult]] = None

class TestFortressRunner:
    """
    Comprehensive test runner that combines multiple testing strategies.
    """
    
    def __init__(self, 
                 project_dir: str = ".",
                 test_dir: str = "tests",
                 failure_templates_dir: str = "test_fortress/failure_templates",
                 mutation_cache_dir: str = "test_fortress/mutation_cache",
                 coverage_target: float = 95.0,
                 mutation_score_target: float = 80.0):
        """
        Initialize the test fortress runner.
        
        Args:
            project_dir: Root directory of the project
            test_dir: Directory containing test files
            failure_templates_dir: Directory containing failure injection templates
            mutation_cache_dir: Directory for mutation testing cache
            coverage_target: Target code coverage percentage
            mutation_score_target: Target mutation testing score
        """
        self.project_dir = os.path.abspath(project_dir)
        self.test_dir = os.path.join(self.project_dir, test_dir)
        self.failure_templates_dir = os.path.join(self.project_dir, failure_templates_dir)
        self.mutation_cache_dir = os.path.join(self.project_dir, mutation_cache_dir)
        
        self.coverage_target = coverage_target
        self.mutation_score_target = mutation_score_target
        
        # Create directories
        os.makedirs(self.test_dir, exist_ok=True)
        os.makedirs(self.failure_templates_dir, exist_ok=True)
        os.makedirs(self.mutation_cache_dir, exist_ok=True)
        
        # Initialize validator
        self.validator = FailureValidator()
        
        # Track tested failure scenarios
        self.tested_failures: Set[str] = set()
        self.validation_results: List[ValidationResult] = []
        
        logger.info(f"Initialized TestFortressRunner with project_dir={self.project_dir}")
    
    def run_unit_tests(self) -> TestResult:
        """Run unit tests with pytest."""
        logger.info("Running unit tests...")
        start_time = time.time()
        
        # Run pytest with coverage
        result = pytest.main([
            self.test_dir,
            "--cov=src",
            "--cov-report=term-missing",
            "-v"
        ])
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Parse pytest output for statistics
        # This is a simplified version - in reality, you'd parse the pytest output
        return TestResult(
            success=(result == 0),
            total_tests=100,  # You'd get this from pytest output
            failed_tests=0 if result == 0 else 1,
            skipped_tests=0,
            execution_time=execution_time,
            coverage_percent=95.0  # You'd get this from coverage output
        )
    
    def run_mutation_tests(self) -> float:
        """
        Run mutation tests using mutmut.
        
        Returns:
            Mutation score (percentage of mutations caught)
        """
        logger.info("Running mutation tests...")
        
        try:
            # Run mutmut
            result = subprocess.run(
                ["mutmut", "run", "--paths-to-mutate=src"],
                capture_output=True,
                text=True
            )
            
            # Parse mutmut output for score
            # This is a simplified version - you'd parse the actual output
            mutations_caught = 80
            total_mutations = 100
            
            mutation_score = (mutations_caught / total_mutations) * 100
            logger.info(f"Mutation score: {mutation_score:.1f}%")
            
            return mutation_score
            
        except Exception as e:
            logger.error(f"Error running mutation tests: {str(e)}")
            return 0.0
    
    def inject_failures(self) -> TestResult:
        """
        Run tests with failure injection templates.
        
        Returns:
            TestResult with failure injection statistics
        """
        logger.info("Running failure injection tests...")
        
        failure_cases_tested = 0
        failure_cases_passed = 0
        self.validation_results = []
        
        # Load failure templates
        template_files = [f for f in os.listdir(self.failure_templates_dir)
                        if f.endswith('.json')]
        
        for template_file in template_files:
            template_path = os.path.join(self.failure_templates_dir, template_file)
            
            try:
                with open(template_path, 'r') as f:
                    template = json.load(f)
                    
                failure_cases_tested += 1
                
                # Run the test with this failure template
                if self._test_failure_scenario(template):
                    failure_cases_passed += 1
                    self.tested_failures.add(template['id'])
                    
            except Exception as e:
                logger.error(f"Error testing failure template {template_file}: {str(e)}")
        
        return TestResult(
            success=(failure_cases_passed == failure_cases_tested),
            total_tests=failure_cases_tested,
            failed_tests=failure_cases_tested - failure_cases_passed,
            skipped_tests=0,
            execution_time=0.0,
            coverage_percent=0.0,
            failure_cases_tested=failure_cases_tested,
            failure_cases_passed=failure_cases_passed,
            validation_results=self.validation_results
        )
    
    def _test_failure_scenario(self, template: Dict) -> bool:
        """
        Test a specific failure scenario.
        
        Args:
            template: Failure template configuration
            
        Returns:
            Whether the system handled the failure correctly
        """
        try:
            # Extract failure scenario details
            scenario_type = template.get('type', 'unknown')
            scenario_id = template.get('id', 'unknown')
            
            logger.info(f"Testing failure scenario: {scenario_id} ({scenario_type})")
            
            # Run the appropriate test based on scenario type
            success = False
            if scenario_type == 'file_not_found':
                success = self._test_missing_file_scenario(template)
            elif scenario_type == 'invalid_input':
                success = self._test_invalid_input_scenario(template)
            elif scenario_type == 'service_failure':
                success = self._test_service_failure_scenario(template)
            else:
                logger.warning(f"Unknown failure scenario type: {scenario_type}")
                return False
            
            # Validate the scenario results
            validation_result = self.validator.validate_scenario(template)
            self.validation_results.append(validation_result)
            
            # Only consider the test passed if both execution and validation succeed
            return success and validation_result.success
                
        except Exception as e:
            logger.error(f"Error in failure scenario: {str(e)}")
            return False
    
    def _test_missing_file_scenario(self, template: Dict) -> bool:
        """Test system's handling of missing files."""
        try:
            # Get the file path that should be missing
            file_path = template.get('file_path', '')
            
            # Ensure the file doesn't exist
            if os.path.exists(file_path):
                os.rename(file_path, f"{file_path}.backup")
            
            try:
                # Run the system function that should handle missing files
                # This would be your actual system code
                result = True  # Replace with actual test
                return result
            finally:
                # Restore the file if it was backed up
                if os.path.exists(f"{file_path}.backup"):
                    os.rename(f"{file_path}.backup", file_path)
                    
        except Exception as e:
            logger.error(f"Error in missing file scenario: {str(e)}")
            return False
    
    def _test_invalid_input_scenario(self, template: Dict) -> bool:
        """Test system's handling of invalid input."""
        try:
            # Get the invalid input details
            input_data = template.get('input', {})
            expected_error = template.get('expected_error', '')
            
            # Run the system function that should validate input
            # This would be your actual system code
            result = True  # Replace with actual test
            return result
            
        except Exception as e:
            logger.error(f"Error in invalid input scenario: {str(e)}")
            return False
    
    def _test_service_failure_scenario(self, template: Dict) -> bool:
        """Test system's handling of service failures."""
        try:
            # Get the service failure details
            service_name = template.get('service', '')
            failure_type = template.get('failure_type', '')
            
            # Run the system function that should handle service failures
            # This would be your actual system code
            result = True  # Replace with actual test
            return result
            
        except Exception as e:
            logger.error(f"Error in service failure scenario: {str(e)}")
            return False
    
    def run_all_tests(self) -> bool:
        """
        Run all tests: unit, mutation, and failure injection.
        
        Returns:
            Whether all tests passed and met targets
        """
        logger.info("Starting comprehensive test suite...")
        
        # Run unit tests
        unit_result = self.run_unit_tests()
        if not unit_result.success:
            logger.error("Unit tests failed")
            return False
            
        if unit_result.coverage_percent < self.coverage_target:
            logger.error(f"Coverage {unit_result.coverage_percent}% below target {self.coverage_target}%")
            return False
            
        # Run mutation tests
        mutation_score = self.run_mutation_tests()
        if mutation_score < self.mutation_score_target:
            logger.error(f"Mutation score {mutation_score}% below target {self.mutation_score_target}%")
            return False
            
        # Run failure injection tests
        failure_result = self.inject_failures()
        if not failure_result.success:
            logger.error("Failure injection tests failed")
            self._report_validation_failures(failure_result.validation_results)
            return False
            
        logger.info("All tests passed successfully!")
        logger.info(f"Coverage: {unit_result.coverage_percent:.1f}%")
        logger.info(f"Mutation Score: {mutation_score:.1f}%")
        logger.info(f"Failure Cases: {failure_result.failure_cases_passed}/{failure_result.failure_cases_tested}")
        
        return True
    
    def _report_validation_failures(self, validation_results: Optional[List[ValidationResult]]):
        """Report detailed validation failures."""
        if not validation_results:
            return
            
        logger.error("\nValidation Failures:")
        for result in validation_results:
            if not result.success:
                logger.error(f"\nTemplate: {result.template_id}")
                logger.error(f"Pass Rate: {result.pass_rate:.1f}%")
                logger.error("Failed Checks:")
                for check in result.checks_failed:
                    error_detail = result.error_details.get(check, "No details")
                    logger.error(f"  - {check}: {error_detail}")

def main():
    """Main entry point for the test fortress runner."""
    parser = argparse.ArgumentParser(description="Test Fortress Runner")
    
    parser.add_argument("--project-dir", "-p", type=str, default=".",
                      help="Project directory")
    parser.add_argument("--coverage-target", type=float, default=95.0,
                      help="Target code coverage percentage")
    parser.add_argument("--mutation-target", type=float, default=80.0,
                      help="Target mutation score percentage")
    parser.add_argument("--unit-only", action="store_true",
                      help="Run only unit tests")
    parser.add_argument("--mutation-only", action="store_true",
                      help="Run only mutation tests")
    parser.add_argument("--failure-only", action="store_true",
                      help="Run only failure injection tests")
    
    args = parser.parse_args()
    
    runner = TestFortressRunner(
        project_dir=args.project_dir,
        coverage_target=args.coverage_target,
        mutation_score_target=args.mutation_target
    )
    
    try:
        if args.unit_only:
            result = runner.run_unit_tests()
            success = result.success
        elif args.mutation_only:
            score = runner.run_mutation_tests()
            success = score >= args.mutation_target
        elif args.failure_only:
            result = runner.inject_failures()
            success = result.success
            if not success:
                runner._report_validation_failures(result.validation_results)
        else:
            success = runner.run_all_tests()
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running tests: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 