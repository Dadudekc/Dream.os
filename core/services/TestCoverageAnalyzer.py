#!/usr/bin/env python3
"""
TestCoverageAnalyzer.py

Provides analysis of test coverage, tracking coverage metrics over time,
and identifying areas needing improved test coverage.
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from datetime import datetime
import re
import difflib

try:
    import coverage
    HAS_COVERAGE_MODULE = True
except ImportError:
    HAS_COVERAGE_MODULE = False

class TestCoverageAnalyzer:
    """
    Analyzes code test coverage, tracks coverage changes over time,
    and provides recommendations for additional tests to write.
    """
    
    def __init__(self, project_root: str = ".", 
                coverage_dir: str = ".coverage_data",
                logger=None):
        """
        Initialize the test coverage analyzer.
        
        Args:
            project_root: Base directory of the project
            coverage_dir: Directory to store coverage data
            logger: Optional custom logger
        """
        self.project_root = Path(project_root)
        self.coverage_dir = self.project_root / coverage_dir
        self.logger = logger or logging.getLogger("TestCoverageAnalyzer")
        
        # Create the coverage directory if it doesn't exist
        self.coverage_dir.mkdir(parents=True, exist_ok=True)
        
        self.history_file = self.coverage_dir / "coverage_history.json"
        self._load_coverage_history()
        
        # Track covered and uncovered functions
        self.current_coverage_data = {}
        
        # Check for coverage module
        if not HAS_COVERAGE_MODULE:
            self.logger.warning("Python 'coverage' module not available. Limited functionality.")

    def _load_coverage_history(self):
        """Load the coverage history from disk."""
        self.coverage_history = {}
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    self.coverage_history = json.load(f)
                self.logger.debug(f"Loaded coverage history for {len(self.coverage_history)} files")
            except Exception as e:
                self.logger.error(f"Failed to load coverage history: {e}")
                # Create a new empty history
                self.coverage_history = {}

    def _save_coverage_history(self):
        """Save the coverage history to disk."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.coverage_history, f, indent=2)
            self.logger.debug(f"Saved coverage history for {len(self.coverage_history)} files")
        except Exception as e:
            self.logger.error(f"Failed to save coverage history: {e}")

    def run_coverage_analysis(self, 
                             target_file: str, 
                             test_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Run coverage analysis on a specific file or test file.
        
        Args:
            target_file: Source file to analyze
            test_file: Test file to run (if None, will attempt to find the corresponding test)
            
        Returns:
            Dictionary containing coverage results
        """
        if not HAS_COVERAGE_MODULE:
            self.logger.warning("Coverage analysis requires the 'coverage' module. Please install with 'pip install coverage'")
            return {"error": "Coverage module not available"}
            
        target_path = Path(target_file)
        if not target_path.exists():
            self.logger.error(f"Target file does not exist: {target_file}")
            return {"error": f"Target file not found: {target_file}"}
            
        # Find the test file if not provided
        if test_file is None:
            test_file = self._find_test_file(target_file)
            if test_file is None:
                self.logger.warning(f"No test file found for {target_file}")
                return {"error": f"No test file found for {target_file}"}
        
        test_path = Path(test_file)
        if not test_path.exists():
            self.logger.error(f"Test file does not exist: {test_file}")
            return {"error": f"Test file not found: {test_file}"}
            
        self.logger.info(f"Running coverage analysis on {target_file} using test {test_file}")
        
        # Run the coverage analysis
        try:
            # Create a coverage object
            cov = coverage.Coverage(
                source=[os.path.dirname(target_file)],
                omit=["*/__pycache__/*", "*/\.*", "*/site-packages/*", "*/.venv/*"]
            )
            
            # Start coverage measurement
            cov.start()
            
            # Run the test file
            result = self._run_test_file(test_file)
            
            # Stop coverage measurement
            cov.stop()
            
            # Analyze the coverage data
            cov.save()
            cov.load()
            
            # Get coverage data for the target file
            file_coverage = {}
            
            # Convert to absolute path for coverage module
            abs_target = os.path.abspath(target_file)
            
            # Get line coverage data
            file_data = cov.get_data()
            if abs_target in file_data.measured_files():
                line_data = file_data.lines(abs_target)
                
                # Read the file content to analyze functions
                with open(target_file, 'r', encoding='utf-8') as f:
                    file_content = f.readlines()
                
                # Analyze function coverage
                function_coverage = self._analyze_function_coverage(file_content, line_data)
                
                # Create the coverage report
                file_coverage = {
                    "file": target_file,
                    "test_file": test_file,
                    "timestamp": datetime.now().isoformat(),
                    "total_lines": len(file_content),
                    "covered_lines": len(line_data),
                    "coverage_percentage": round((len(line_data) / len(file_content)) * 100, 2),
                    "functions": function_coverage,
                    "test_result": result,
                }
                
                # Update the history
                self._update_coverage_history(target_file, file_coverage)
                
                # Store the current coverage data
                self.current_coverage_data[target_file] = file_coverage
                
                return file_coverage
            else:
                self.logger.warning(f"No coverage data found for {target_file}")
                return {"error": f"No coverage data found for {target_file}"}
                
        except Exception as e:
            self.logger.error(f"Error during coverage analysis: {e}")
            return {"error": f"Coverage analysis failed: {e}"}

    def _find_test_file(self, target_file: str) -> Optional[str]:
        """Find the corresponding test file for a source file."""
        target_path = Path(target_file)
        
        # Common test file naming patterns
        patterns = [
            f"test_{target_path.name}",
            f"{target_path.stem}_test{target_path.suffix}",
            f"{target_path.stem}.test{target_path.suffix}",
        ]
        
        # Check the same directory first
        for pattern in patterns:
            test_path = target_path.parent / pattern
            if test_path.exists():
                return str(test_path)
        
        # Check for a 'tests' directory at the same level
        tests_dir = target_path.parent / "tests"
        if tests_dir.exists() and tests_dir.is_dir():
            for pattern in patterns:
                test_path = tests_dir / pattern
                if test_path.exists():
                    return str(test_path)
        
        # Check for a 'test' directory at the same level
        test_dir = target_path.parent / "test"
        if test_dir.exists() and test_dir.is_dir():
            for pattern in patterns:
                test_path = test_dir / pattern
                if test_path.exists():
                    return str(test_path)
        
        # Check for tests in parent directory
        parent_test_dir = target_path.parent.parent / "tests"
        if parent_test_dir.exists() and parent_test_dir.is_dir():
            for pattern in patterns:
                test_path = parent_test_dir / pattern
                if test_path.exists():
                    return str(test_path)
                    
        return None

    def _run_test_file(self, test_file: str) -> Dict[str, Any]:
        """Run a test file and return the results."""
        test_path = Path(test_file)
        
        if test_path.suffix == '.py':
            # For Python tests
            try:
                result = subprocess.run(
                    ["python", str(test_path)],
                    capture_output=True,
                    text=True,
                    cwd=str(self.project_root)
                )
                
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }
                
            except Exception as e:
                self.logger.error(f"Error running test file {test_file}: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
                
        elif test_path.suffix in ['.js', '.ts', '.jsx', '.tsx']:
            # For JavaScript/TypeScript tests
            try:
                # Check for npm test runner
                if (test_path.parent / "package.json").exists():
                    # Assumes npm test configuration
                    result = subprocess.run(
                        ["npm", "test", "--", str(test_path)],
                        capture_output=True,
                        text=True,
                        cwd=str(test_path.parent)
                    )
                else:
                    # Assumes jest is installed globally
                    result = subprocess.run(
                        ["jest", str(test_path)],
                        capture_output=True,
                        text=True,
                        cwd=str(self.project_root)
                    )
                
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }
                
            except Exception as e:
                self.logger.error(f"Error running test file {test_file}: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        else:
            self.logger.warning(f"Unsupported test file type: {test_path.suffix}")
            return {
                "success": False,
                "error": f"Unsupported test file type: {test_path.suffix}"
            }

    def _analyze_function_coverage(self, 
                                  file_content: List[str], 
                                  covered_lines: Set[int]) -> Dict[str, Any]:
        """
        Analyze function coverage by identifying functions and checking if they're covered.
        
        Args:
            file_content: List of file lines
            covered_lines: Set of covered line numbers
            
        Returns:
            Dictionary with function coverage information
        """
        function_coverage = {
            "covered_functions": [],
            "partially_covered_functions": [],
            "uncovered_functions": []
        }
        
        # Extract functions and classes
        current_function = None
        current_class = None
        function_lines = {}
        in_function = False
        function_start_line = 0
        indentation_level = 0
        
        for line_num, line in enumerate(file_content, 1):
            # Check for class definitions
            class_match = re.match(r'^\s*class\s+(\w+)', line)
            if class_match:
                current_class = class_match.group(1)
                continue
                
            # Check for function/method definitions
            func_match = re.match(r'^\s*def\s+(\w+)', line)
            if func_match and not in_function:
                function_name = func_match.group(1)
                if current_class:
                    if function_name != '__init__':  # Skip __init__ methods
                        current_function = f"{current_class}.{function_name}"
                    else:
                        current_function = None
                else:
                    current_function = function_name
                    
                if current_function:
                    in_function = True
                    function_start_line = line_num
                    indentation_level = len(line) - len(line.lstrip())
                    function_lines[current_function] = []
                    
            # Track lines in the current function
            if in_function and current_function:
                function_lines[current_function].append(line_num)
                
                # Check if we've exited the function (based on indentation)
                if line.strip() and len(line) - len(line.lstrip()) <= indentation_level:
                    # Process the completed function
                    self._add_function_coverage(
                        function_coverage, 
                        current_function, 
                        function_lines[current_function],
                        covered_lines
                    )
                    
                    # Reset function tracking
                    in_function = False
                    current_function = None
                    
        # Handle the last function
        if in_function and current_function:
            self._add_function_coverage(
                function_coverage, 
                current_function, 
                function_lines[current_function],
                covered_lines
            )
            
        return function_coverage

    def _add_function_coverage(self, 
                              function_coverage: Dict[str, Any], 
                              function_name: str, 
                              lines: List[int], 
                              covered_lines: Set[int]):
        """Add a function to the appropriate coverage category."""
        covered_count = sum(1 for line in lines if line in covered_lines)
        coverage_percentage = (covered_count / len(lines)) * 100 if lines else 0
        
        function_data = {
            "name": function_name,
            "total_lines": len(lines),
            "covered_lines": covered_count,
            "coverage_percentage": round(coverage_percentage, 2),
            "line_range": [min(lines), max(lines)] if lines else [0, 0]
        }
        
        if coverage_percentage == 0:
            function_coverage["uncovered_functions"].append(function_data)
        elif coverage_percentage < 100:
            function_coverage["partially_covered_functions"].append(function_data)
        else:
            function_coverage["covered_functions"].append(function_data)

    def _update_coverage_history(self, target_file: str, coverage_data: Dict[str, Any]):
        """Update the history for a target file with new coverage data."""
        if target_file not in self.coverage_history:
            self.coverage_history[target_file] = []
            
        # Add new entry
        history_entry = {
            "timestamp": coverage_data["timestamp"],
            "coverage_percentage": coverage_data["coverage_percentage"],
            "covered_functions": len(coverage_data["functions"]["covered_functions"]),
            "partially_covered_functions": len(coverage_data["functions"]["partially_covered_functions"]),
            "uncovered_functions": len(coverage_data["functions"]["uncovered_functions"])
        }
        
        self.coverage_history[target_file].append(history_entry)
        
        # Save the updated history
        self._save_coverage_history()

    def get_coverage_report(self, target_file: str) -> Dict[str, Any]:
        """
        Get the coverage report for a target file.
        
        Args:
            target_file: The file to get coverage for
            
        Returns:
            Dictionary with coverage information
        """
        # If not yet analyzed, attempt to run analysis
        if target_file not in self.current_coverage_data:
            test_file = self._find_test_file(target_file)
            if test_file:
                self.run_coverage_analysis(target_file, test_file)
        
        # If still not available, check if file exists
        if target_file not in self.current_coverage_data:
            target_path = Path(target_file)
            if not target_path.exists():
                return {"error": f"Target file not found: {target_file}"}
                
            # File exists but no tests
            return {
                "file": target_file,
                "current_coverage": 0,
                "trend": "unknown",
                "history": [],
                "uncovered_functions": []
            }
            
        # Get the current coverage data
        coverage_data = self.current_coverage_data[target_file]
        
        # Calculate the trend
        trend = "unknown"
        if target_file in self.coverage_history and len(self.coverage_history[target_file]) >= 2:
            history = self.coverage_history[target_file]
            current = history[-1]["coverage_percentage"]
            previous = history[-2]["coverage_percentage"]
            
            if current > previous:
                trend = "increasing"
            elif current < previous:
                trend = "decreasing"
            else:
                trend = "stable"
                
        # Extract uncovered functions
        uncovered_functions = []
        for func in coverage_data["functions"]["uncovered_functions"]:
            uncovered_functions.append({
                "function": func["name"],
                "line_range": func["line_range"]
            })
            
        # Extract partially covered functions
        partially_covered = []
        for func in coverage_data["functions"]["partially_covered_functions"]:
            partially_covered.append({
                "function": func["name"],
                "coverage": func["coverage_percentage"],
                "line_range": func["line_range"]
            })
            
        return {
            "file": target_file,
            "current_coverage": coverage_data["coverage_percentage"],
            "trend": trend,
            "total_lines": coverage_data["total_lines"],
            "covered_lines": coverage_data["covered_lines"],
            "history": self.coverage_history.get(target_file, []),
            "uncovered_functions": uncovered_functions,
            "partially_covered_functions": partially_covered
        }

    def generate_coverage_diff(self, target_file: str, 
                              before_coverage: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a diff of coverage before and after changes.
        
        Args:
            target_file: The file to compare coverage for
            before_coverage: Previous coverage data (optional)
            
        Returns:
            Dictionary with coverage diff information
        """
        # Get current coverage
        current_coverage = self.get_coverage_report(target_file)
        
        # If no previous coverage provided, use the most recent history entry
        if before_coverage is None and target_file in self.coverage_history:
            history = self.coverage_history[target_file]
            if len(history) >= 2:
                # Get data from the previous run
                prev_timestamp = history[-2]["timestamp"]
                prev_percent = history[-2]["coverage_percentage"]
                prev_uncovered = history[-2]["uncovered_functions"]
                
                before_coverage = {
                    "timestamp": prev_timestamp,
                    "coverage_percentage": prev_percent,
                    "uncovered_functions": prev_uncovered
                }
            
        # If no previous coverage data available, return only current
        if before_coverage is None:
            return {
                "current": current_coverage,
                "previous": None,
                "diff": None
            }
            
        # Calculate diff
        diff = {
            "coverage_change": current_coverage["current_coverage"] - before_coverage["coverage_percentage"],
            "newly_covered_functions": [],
            "still_uncovered_functions": []
        }
        
        # Find newly covered functions
        current_uncovered = set(f["function"] for f in current_coverage["uncovered_functions"])
        if "uncovered_functions" in before_coverage:
            prev_uncovered = set(before_coverage["uncovered_functions"])
            
            # Functions that were uncovered before but are now covered
            newly_covered = prev_uncovered - current_uncovered
            diff["newly_covered_functions"] = list(newly_covered)
            
            # Functions that are still uncovered
            diff["still_uncovered_functions"] = list(current_uncovered)
            
        return {
            "current": current_coverage,
            "previous": before_coverage,
            "diff": diff
        }

    def recommend_test_improvements(self, target_file: str) -> Dict[str, Any]:
        """
        Recommend test improvements for a target file.
        
        Args:
            target_file: The file to generate recommendations for
            
        Returns:
            Dictionary with test improvement recommendations
        """
        coverage_report = self.get_coverage_report(target_file)
        
        # If coverage analysis failed, return error
        if "error" in coverage_report:
            return {"error": coverage_report["error"]}
            
        # Define recommendations
        recommendations = {
            "file": target_file,
            "current_coverage": coverage_report["current_coverage"],
            "recommended_test_strategies": [],
            "recommended_test_focus": []
        }
        
        # Recommend strategies based on coverage
        if coverage_report["current_coverage"] == 0:
            recommendations["recommended_test_strategies"].append(
                "Create an initial test suite covering basic functionality"
            )
        elif coverage_report["current_coverage"] < 50:
            recommendations["recommended_test_strategies"].append(
                "Significantly improve test coverage by focusing on core functions"
            )
        elif coverage_report["current_coverage"] < 80:
            recommendations["recommended_test_strategies"].append(
                "Add tests for edge cases and error conditions to improve coverage"
            )
        else:
            recommendations["recommended_test_strategies"].append(
                "Focus on maintaining high test coverage as code changes"
            )
            
        # Add specific recommendations for uncovered functions
        for func in coverage_report["uncovered_functions"]:
            function_name = func["function"]
            
            # Set priority
            priority = "high"
            if "." in function_name:  # Likely a class method
                if function_name.endswith(".__init__"):
                    # Constructor tests are important
                    priority = "high"
                elif any(p in function_name for p in ["_get", "_set", "_create", "_delete", "_update"]):
                    # Internal helper methods can be medium priority
                    priority = "medium"
                    
            recommendations["recommended_test_focus"].append({
                "function": function_name,
                "priority": priority,
                "line_range": func["line_range"],
                "recommendation": f"Create tests for {function_name}() function"
            })
            
        # Add recommendations for partially covered functions
        for func in coverage_report.get("partially_covered_functions", []):
            function_name = func["function"]
            coverage = func["coverage"]
            
            if coverage < 50:
                priority = "high"
                recommendation = f"Improve test coverage for {function_name}() (currently at {coverage}%)"
            else:
                priority = "medium"
                recommendation = f"Add tests for edge cases in {function_name}() to improve coverage"
                
            recommendations["recommended_test_focus"].append({
                "function": function_name,
                "priority": priority,
                "coverage": coverage,
                "line_range": func["line_range"],
                "recommendation": recommendation
            })
            
        # Sort recommendations by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations["recommended_test_focus"].sort(
            key=lambda x: (priority_order[x["priority"]], x.get("coverage", 0))
        )
        
        return recommendations

    def analyze_uncovered_code(self, target_file: str) -> Dict[str, Any]:
        """
        Analyze uncovered code to determine why it's not covered.
        
        Args:
            target_file: The file to analyze
            
        Returns:
            Dictionary with analysis of uncovered code
        """
        coverage_report = self.get_coverage_report(target_file)
        
        # If coverage analysis failed, return error
        if "error" in coverage_report:
            return {"error": coverage_report["error"]}
            
        # Read the file content
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                file_content = f.readlines()
        except Exception as e:
            return {"error": f"Failed to read file: {e}"}
            
        # Analyze uncovered functions
        uncovered_analysis = []
        
        for func in coverage_report["uncovered_functions"]:
            function_name = func["function"]
            line_range = func["line_range"]
            
            # Extract function code
            func_code = "".join(file_content[line_range[0]-1:line_range[1]])
            
            # Analyze why it might be uncovered
            reason = self._determine_uncovered_reason(func_code, function_name)
            
            uncovered_analysis.append({
                "function": function_name,
                "line_range": line_range,
                "reason": reason,
                "recommended_approach": self._recommend_test_approach(reason, function_name)
            })
            
        # Analyze partially covered functions
        partial_analysis = []
        
        for func in coverage_report.get("partially_covered_functions", []):
            function_name = func["function"]
            line_range = func["line_range"]
            coverage = func["coverage"]
            
            # Extract function code
            func_code = "".join(file_content[line_range[0]-1:line_range[1]])
            
            # Analyze what parts are uncovered
            uncovered_patterns = self._identify_uncovered_patterns(func_code)
            
            partial_analysis.append({
                "function": function_name,
                "coverage": coverage,
                "line_range": line_range,
                "uncovered_patterns": uncovered_patterns,
                "recommended_approach": self._recommend_test_approach_for_partial(uncovered_patterns, function_name)
            })
            
        return {
            "file": target_file,
            "uncovered_functions_analysis": uncovered_analysis,
            "partially_covered_functions_analysis": partial_analysis,
            "overall_assessment": self._generate_overall_assessment(coverage_report)
        }
        
    def _determine_uncovered_reason(self, func_code: str, function_name: str) -> str:
        """Determine why a function might be uncovered by tests."""
        if "raise" in func_code and any(e in func_code for e in ["Exception", "Error"]):
            return "error_handler"
        elif "if __name__ == '__main__'" in func_code:
            return "main_block"
        elif "_" == function_name[0]:
            return "private_function"
        elif any(p in func_code for p in ["abstract", "@abstractmethod"]):
            return "abstract_method"
        elif len(func_code.split("\n")) <= 3:
            return "trivial_function"
        else:
            return "unwritten_tests"
            
    def _identify_uncovered_patterns(self, func_code: str) -> List[str]:
        """Identify patterns that typically indicate uncovered code."""
        patterns = []
        
        if "if" in func_code and "else" in func_code:
            patterns.append("conditional_branches")
        if "try" in func_code and "except" in func_code:
            patterns.append("exception_handling")
        if "while" in func_code:
            patterns.append("loops")
        if "raise" in func_code:
            patterns.append("exceptions")
            
        return patterns or ["general_coverage_gaps"]
        
    def _recommend_test_approach(self, reason: str, function_name: str) -> str:
        """Recommend a testing approach based on the reason for lack of coverage."""
        if reason == "error_handler":
            return f"Write tests that trigger error conditions to cover {function_name}"
        elif reason == "main_block":
            return "Main blocks can be tested through integration or command-line tests"
        elif reason == "private_function":
            return f"Test {function_name} indirectly through public interfaces"
        elif reason == "abstract_method":
            return "Test concrete implementations instead of abstract methods"
        elif reason == "trivial_function":
            return f"Simple unit test for {function_name} to ensure basic functionality"
        else:
            return f"Write comprehensive tests for {function_name} with various inputs"
            
    def _recommend_test_approach_for_partial(self, patterns: List[str], function_name: str) -> str:
        """Recommend how to improve partial test coverage."""
        if "conditional_branches" in patterns:
            return f"Add tests for different branches in {function_name}"
        elif "exception_handling" in patterns:
            return f"Add tests that trigger exception handling in {function_name}"
        elif "loops" in patterns:
            return f"Add tests with different iteration counts for loops in {function_name}"
        elif "exceptions" in patterns:
            return f"Add tests that trigger exceptions in {function_name}"
        else:
            return f"Add more tests with edge cases for {function_name}"
            
    def _generate_overall_assessment(self, coverage_report: Dict[str, Any]) -> str:
        """Generate an overall assessment of test coverage."""
        coverage = coverage_report["current_coverage"]
        
        if coverage == 0:
            return "No test coverage. Immediate action needed to create tests."
        elif coverage < 30:
            return "Very low test coverage. High priority to add basic tests."
        elif coverage < 60:
            return "Moderate test coverage. Continue adding tests for uncovered functions."
        elif coverage < 80:
            return "Good test coverage. Focus on edge cases and partially covered areas."
        else:
            return "Excellent test coverage. Maintain coverage as code evolves." 