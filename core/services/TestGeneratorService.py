#!/usr/bin/env python3
"""
TestGeneratorService - Automated test generation with coverage enhancement
=========================================================================

Generates test skeletons for various file types, using a coverage-driven approach
to focus on untested functionality. Supports feedback-based regeneration to
continually improve test quality based on execution results.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)

class TestGeneratorService:
    """
    Service for generating and regenerating tests with coverage enhancement.
    
    This service can:
    - Generate initial test skeletons for a target file
    - Analyze coverage and generate targeted tests for uncovered functions
    - Regenerate or augment tests based on execution feedback
    - Maintain a history of test generation
    """
    
    def __init__(self, 
                 openai_client=None, 
                 project_root: str = ".", 
                 history_dir: str = None,
                 coverage_analyzer=None):
        """
        Initialize the test generator service.
        
        Args:
            openai_client: OpenAI client for generating test code
            project_root: Root directory of the project
            history_dir: Directory to store test generation history
            coverage_analyzer: Coverage analyzer for coverage-driven test generation
        """
        self._openai_client = openai_client
        self._project_root = project_root
        
        # Set default history directory if not provided
        if not history_dir:
            history_dir = os.path.join(project_root, "test_generation_history")
        self._history_dir = history_dir
        os.makedirs(history_dir, exist_ok=True)
        
        # Set the coverage analyzer
        self._coverage_analyzer = coverage_analyzer
        
        # Load generation history
        self._generation_history = {}
        history_file = os.path.join(self._history_dir, "generation_history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    self._generation_history = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load generation history: {e}")
        
        logger.info(f"TestGeneratorService initialized with project root: {project_root}")
    
    def generate_tests(self, 
                      target_file_path: str, 
                      mode: str = "tdd",
                      test_framework: str = None) -> Dict[str, Any]:
        """
        Generate test skeletons for a target file.
        
        Args:
            target_file_path: Path to the file to generate tests for
            mode: Test generation mode (tdd, post_implementation, coverage_driven)
            test_framework: Test framework to use (e.g., pytest, jest)
            
        Returns:
            Dict containing the generated test skeleton and metadata
        """
        logger.info(f"Generating tests for {target_file_path} using mode: {mode}")
        
        # Check if the target file exists
        if not os.path.exists(target_file_path):
            logger.error(f"Target file {target_file_path} does not exist")
            return {"error": "Target file does not exist"}
        
        # Read the target file
        try:
            with open(target_file_path, "r") as f:
                target_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read target file: {e}")
            return {"error": f"Failed to read target file: {e}"}
        
        # Determine file extension and test framework if not provided
        file_ext = os.path.splitext(target_file_path)[1].lower()
        if not test_framework:
            if file_ext == ".py":
                test_framework = "pytest"
            elif file_ext in [".js", ".ts", ".jsx", ".tsx"]:
                test_framework = "jest"
            else:
                test_framework = "generic"
        
        # Generate tests based on the mode
        result = {}
        
        if mode == "tdd":
            # Generate tests before implementation (TDD)
            result = self._generate_tdd_tests(target_file_path, target_content, test_framework)
        elif mode == "post_implementation":
            # Generate tests for existing implementation
            result = self._generate_post_implementation_tests(target_file_path, target_content, test_framework)
        elif mode == "coverage_driven":
            # Generate tests based on coverage analysis
            result = self._generate_coverage_driven_tests(target_file_path, target_content, test_framework)
        else:
            logger.error(f"Unknown mode: {mode}")
            return {"error": f"Unknown mode: {mode}"}
        
        # Update generation history
        self._update_generation_history(target_file_path, result, mode)
        
        return result
    
    def regenerate_tests_based_on_feedback(self, 
                                          target_file_path: str, 
                                          feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Regenerate or augment tests based on test execution feedback.
        
        Args:
            target_file_path: Path to the target file
            feedback: Dictionary containing test execution feedback
                {
                    "test_file": "path/to/test_file.py",
                    "test_output": "Output from test execution",
                    "passing_tests": ["test_1", "test_2"],
                    "failing_tests": ["test_3", "test_4"],
                    "coverage_report": "Optional coverage report"
                }
                
        Returns:
            Dict containing the regenerated test skeleton and metadata
        """
        logger.info(f"Regenerating tests for {target_file_path} based on feedback")
        
        # Check if the target file exists
        if not os.path.exists(target_file_path):
            logger.error(f"Target file {target_file_path} does not exist")
            return {"error": "Target file does not exist"}
        
        # Check if the test file exists
        test_file = feedback.get("test_file")
        if not test_file or not os.path.exists(test_file):
            logger.error(f"Test file {test_file} does not exist")
            return {"error": "Test file does not exist"}
        
        # Read the test file
        try:
            with open(test_file, "r") as f:
                test_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read test file: {e}")
            return {"error": f"Failed to read test file: {e}"}
        
        # Apply feedback to regenerate tests
        result = self._apply_test_feedback(target_file_path, test_file, test_content, feedback)
        
        # Update generation history
        self._update_generation_history(target_file_path, result, "feedback")
        
        return result
    
    def _generate_tdd_tests(self, 
                           target_file_path: str, 
                           target_content: str, 
                           test_framework: str) -> Dict[str, Any]:
        """
        Generate tests using Test-Driven Development approach.
        Focuses on the interface defined in the file without implementation details.
        
        For testing purposes, this just returns a simple test skeleton.
        """
        return {
            "test_file": self._get_test_file_path(target_file_path),
            "test_content": f"# Generated TDD test for {target_file_path}\n\n# This is a placeholder for actual test content",
            "mode": "tdd",
            "test_framework": test_framework,
            "metadata": {
                "generator": "TestGeneratorService",
                "target_file": target_file_path,
                "generation_count": 1
            }
        }
    
    def _generate_post_implementation_tests(self, 
                                          target_file_path: str, 
                                          target_content: str, 
                                          test_framework: str) -> Dict[str, Any]:
        """
        Generate tests for an existing implementation.
        
        For testing purposes, this just returns a simple test skeleton.
        """
        return {
            "test_file": self._get_test_file_path(target_file_path),
            "test_content": f"# Generated post-implementation test for {target_file_path}\n\n# This is a placeholder for actual test content",
            "mode": "post_implementation",
            "test_framework": test_framework,
            "metadata": {
                "generator": "TestGeneratorService",
                "target_file": target_file_path,
                "generation_count": 1
            }
        }
    
    def _generate_coverage_driven_tests(self, 
                                      target_file_path: str, 
                                      target_content: str, 
                                      test_framework: str) -> Dict[str, Any]:
        """
        Generate tests based on coverage analysis, focusing on uncovered functions and edge cases.
        
        Args:
            target_file_path: Path to the target file
            target_content: Content of the target file
            test_framework: Test framework to use
            
        Returns:
            Dict containing the generated test skeleton and metadata
        """
        # Check if coverage analyzer is available
        if not self._coverage_analyzer:
            logger.warning("Coverage analyzer not available, falling back to post-implementation mode")
            return self._generate_post_implementation_tests(target_file_path, target_content, test_framework)
        
        # Check if a test file already exists
        test_file = self._get_test_file_path(target_file_path)
        test_exists = os.path.exists(test_file)
        
        if test_exists:
            # Analyze current coverage and generate focused tests based on recommendations
            logger.info(f"Test file {test_file} exists, analyzing coverage")
            
            # Get coverage report
            coverage_report = self._coverage_analyzer.get_coverage_report(target_file_path)
            
            # Generate tests based on file type
            file_ext = os.path.splitext(target_file_path)[1].lower()
            
            if file_ext == ".py":
                result = self._generate_python_coverage_tests(target_file_path, target_content, test_file, coverage_report)
            elif file_ext in [".js", ".ts", ".jsx", ".tsx"]:
                result = self._generate_js_coverage_tests(target_file_path, target_content, test_file, coverage_report)
            else:
                logger.warning(f"Unsupported file extension for coverage analysis: {file_ext}")
                result = self._generate_post_implementation_tests(target_file_path, target_content, test_framework)
        else:
            # Generate basic test skeleton
            logger.info(f"No test file exists for {target_file_path}, generating a basic skeleton")
            result = self._generate_post_implementation_tests(target_file_path, target_content, test_framework)
        
        # Add mode and test framework to the result
        result["mode"] = "coverage_driven"
        result["test_framework"] = test_framework
        
        return result
    
    def _update_generation_history(self, target_file_path: str, result: Dict[str, Any], mode: str) -> None:
        """
        Update the generation history for a file.
        
        Args:
            target_file_path: Path to the target file
            result: Generated test result
            mode: Generation mode
        """
        # Update the generation count
        if target_file_path not in self._generation_history:
            self._generation_history[target_file_path] = {"generation_count": 0, "modes": []}
        
        self._generation_history[target_file_path]["generation_count"] += 1
        self._generation_history[target_file_path]["modes"].append(mode)
        self._generation_history[target_file_path]["last_mode"] = mode
        self._generation_history[target_file_path]["last_generation"] = result.get("metadata", {})
        
        # Limit the history to the most recent 10 entries
        if "history" not in self._generation_history[target_file_path]:
            self._generation_history[target_file_path]["history"] = []
        
        self._generation_history[target_file_path]["history"].append({
            "mode": mode,
            "timestamp": result.get("metadata", {}).get("timestamp", ""),
            "test_file": result.get("test_file", "")
        })
        
        if len(self._generation_history[target_file_path]["history"]) > 10:
            self._generation_history[target_file_path]["history"] = self._generation_history[target_file_path]["history"][-10:]
        
        # Save the history
        try:
            history_file = os.path.join(self._history_dir, "generation_history.json")
            with open(history_file, "w") as f:
                json.dump(self._generation_history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save generation history: {e}")
    
    def _apply_test_feedback(self, 
                           target_file_path: str, 
                           test_file: str, 
                           test_content: str, 
                           feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply feedback to regenerate tests.
        
        Args:
            target_file_path: Path to the target file
            test_file: Path to the test file
            test_content: Content of the test file
            feedback: Test execution feedback
            
        Returns:
            Dict containing the regenerated test skeleton and metadata
        """
        # Determine file extension
        file_ext = os.path.splitext(target_file_path)[1].lower()
        
        if file_ext == ".py":
            return self._fix_python_tests(target_file_path, test_file, test_content, feedback)
        elif file_ext in [".js", ".ts", ".jsx", ".tsx"]:
            return self._fix_js_tests(target_file_path, test_file, test_content, feedback)
        else:
            logger.warning(f"Unsupported file extension for test fixing: {file_ext}")
            
            # Return placeholder result for unsupported file types
            return {
                "test_file": test_file,
                "test_content": test_content,  # Unchanged
                "mode": "feedback",
                "test_framework": "generic",
                "metadata": {
                    "generator": "TestGeneratorService",
                    "target_file": target_file_path,
                    "generation_count": self._generation_history.get(target_file_path, {}).get("generation_count", 0) + 1,
                    "feedback_applied": False,
                    "reason": f"Unsupported file extension: {file_ext}"
                }
            }
    
    def _augment_passing_tests(self, 
                              target_file_path: str, 
                              test_file: str, 
                              test_content: str, 
                              feedback: Dict[str, Any]) -> str:
        """
        Augment passing tests to improve coverage.
        
        For testing purposes, this just returns the original test content.
        """
        return f"{test_content}\n\n# Augmented tests based on feedback\n# This is a placeholder for actual augmented tests"
    
    def _fix_python_tests(self, 
                         target_file_path: str, 
                         test_file: str, 
                         test_content: str, 
                         feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix failing Python tests based on feedback.
        
        For testing purposes, this just returns a simple fixed test skeleton.
        """
        # Extract failed tests from feedback
        failed_tests = feedback.get("failing_tests", [])
        test_output = feedback.get("test_output", "")
        failed_test_names = self._extract_python_failed_tests(test_output)
        
        # If no failing tests were found, just return the original test content
        if not failed_tests and not failed_test_names:
            return {
                "test_file": test_file,
                "test_content": test_content,  # Unchanged
                "mode": "feedback",
                "test_framework": "pytest",
                "metadata": {
                    "generator": "TestGeneratorService",
                    "target_file": target_file_path,
                    "generation_count": self._generation_history.get(target_file_path, {}).get("generation_count", 0) + 1,
                    "feedback_applied": False,
                    "reason": "No failing tests found"
                }
            }
        
        # Combine failed tests from both sources
        all_failed_tests = set(failed_tests + failed_test_names)
        
        # For testing purposes, just return a placeholder for fixed tests
        fixed_content = test_content
        for test_name in all_failed_tests:
            fixed_content = self._fix_python_test_case(fixed_content, test_name)
        
        return {
            "test_file": test_file,
            "test_content": fixed_content,
            "mode": "feedback",
            "test_framework": "pytest",
            "metadata": {
                "generator": "TestGeneratorService",
                "target_file": target_file_path,
                "generation_count": self._generation_history.get(target_file_path, {}).get("generation_count", 0) + 1,
                "feedback_applied": True,
                "fixed_tests": list(all_failed_tests)
            }
        }
    
    def _fix_js_tests(self, 
                     target_file_path: str, 
                     test_file: str, 
                     test_content: str, 
                     feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix failing JavaScript/TypeScript tests based on feedback.
        
        For testing purposes, this just returns a simple fixed test skeleton.
        """
        # Extract failed tests from feedback
        failed_tests = feedback.get("failing_tests", [])
        test_output = feedback.get("test_output", "")
        failed_test_names = self._extract_js_failed_tests(test_output)
        
        # If no failing tests were found, just return the original test content
        if not failed_tests and not failed_test_names:
            return {
                "test_file": test_file,
                "test_content": test_content,  # Unchanged
                "mode": "feedback",
                "test_framework": "jest",
                "metadata": {
                    "generator": "TestGeneratorService",
                    "target_file": target_file_path,
                    "generation_count": self._generation_history.get(target_file_path, {}).get("generation_count", 0) + 1,
                    "feedback_applied": False,
                    "reason": "No failing tests found"
                }
            }
        
        # Combine failed tests from both sources
        all_failed_tests = set(failed_tests + failed_test_names)
        
        # For testing purposes, just return a placeholder for fixed tests
        fixed_content = test_content
        for test_name in all_failed_tests:
            fixed_content = self._fix_js_test_case(fixed_content, test_name)
        
        return {
            "test_file": test_file,
            "test_content": fixed_content,
            "mode": "feedback",
            "test_framework": "jest",
            "metadata": {
                "generator": "TestGeneratorService",
                "target_file": target_file_path,
                "generation_count": self._generation_history.get(target_file_path, {}).get("generation_count", 0) + 1,
                "feedback_applied": True,
                "fixed_tests": list(all_failed_tests)
            }
        }
    
    def _generate_python_coverage_tests(self, 
                                      target_file_path: str, 
                                      target_content: str, 
                                      test_file: str, 
                                      coverage_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Python tests based on coverage analysis.
        
        For testing purposes, this just returns a simple test skeleton with coverage info.
        """
        return {
            "test_file": test_file,
            "test_content": f"# Coverage-driven tests for {target_file_path}\n\n"
                            f"# Coverage report: {json.dumps(coverage_report, indent=2)}\n\n"
                            f"# This is a placeholder for actual coverage-driven tests",
            "mode": "coverage_driven",
            "test_framework": "pytest",
            "metadata": {
                "generator": "TestGeneratorService",
                "target_file": target_file_path,
                "generation_count": self._generation_history.get(target_file_path, {}).get("generation_count", 0) + 1,
                "coverage": coverage_report
            }
        }
    
    def _generate_js_coverage_tests(self, 
                                  target_file_path: str, 
                                  target_content: str, 
                                  test_file: str, 
                                  coverage_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate JavaScript/TypeScript tests based on coverage analysis.
        
        For testing purposes, this just returns a simple test skeleton with coverage info.
        """
        return {
            "test_file": test_file,
            "test_content": f"// Coverage-driven tests for {target_file_path}\n\n"
                            f"// Coverage report: {json.dumps(coverage_report, indent=2)}\n\n"
                            f"// This is a placeholder for actual coverage-driven tests",
            "mode": "coverage_driven",
            "test_framework": "jest",
            "metadata": {
                "generator": "TestGeneratorService",
                "target_file": target_file_path,
                "generation_count": self._generation_history.get(target_file_path, {}).get("generation_count", 0) + 1,
                "coverage": coverage_report
            }
        }
    
    def _extract_python_failed_tests(self, test_output: str) -> List[str]:
        """
        Extract failed test names from Python test output.
        
        For testing purposes, this just returns an empty list.
        """
        return []
    
    def _extract_js_failed_tests(self, test_output: str) -> List[str]:
        """
        Extract failed test names from JavaScript/TypeScript test output.
        
        For testing purposes, this just returns an empty list.
        """
        return []
    
    def _fix_python_test_case(self, test_content: str, test_name: str) -> str:
        """
        Fix a specific Python test case based on the test name.
        
        For testing purposes, this just adds a comment to the test content.
        """
        return f"{test_content}\n\n# Fixed test case: {test_name}\n# This is a placeholder for the fixed test"
    
    def _fix_js_test_case(self, test_content: str, test_name: str) -> str:
        """
        Fix a specific JavaScript/TypeScript test case based on the test name.
        
        For testing purposes, this just adds a comment to the test content.
        """
        return f"{test_content}\n\n// Fixed test case: {test_name}\n// This is a placeholder for the fixed test"
    
    def _get_test_file_path(self, target_file_path: str) -> str:
        """
        Get the test file path for a target file.
        
        Args:
            target_file_path: Path to the target file
            
        Returns:
            Path to the corresponding test file
        """
        # Get file name and extension
        file_path, file_name = os.path.split(target_file_path)
        file_base, file_ext = os.path.splitext(file_name)
        
        # Determine test file name based on extension
        if file_ext == ".py":
            test_file_name = f"test_{file_base}{file_ext}"
        elif file_ext in [".js", ".jsx"]:
            test_file_name = f"{file_base}.test{file_ext}"
        elif file_ext in [".ts", ".tsx"]:
            test_file_name = f"{file_base}.spec{file_ext}"
        else:
            test_file_name = f"test_{file_name}"
        
        # Determine test directory
        if "test" in file_path or "tests" in file_path:
            # Already in a test directory, use the same directory
            test_file_path = os.path.join(file_path, test_file_name)
        else:
            # Not in a test directory, use the tests directory
            if os.path.exists(os.path.join(file_path, "tests")):
                test_file_path = os.path.join(file_path, "tests", test_file_name)
            elif os.path.exists(os.path.join(file_path, "test")):
                test_file_path = os.path.join(file_path, "test", test_file_name)
            elif os.path.exists(os.path.join(self._project_root, "tests")):
                # Use the project-level tests directory
                test_dir = os.path.join(self._project_root, "tests")
                rel_path = os.path.relpath(file_path, self._project_root)
                test_file_path = os.path.join(test_dir, rel_path, test_file_name)
            else:
                # Fallback to the same directory
                test_file_path = os.path.join(file_path, test_file_name)
        
        return test_file_path 