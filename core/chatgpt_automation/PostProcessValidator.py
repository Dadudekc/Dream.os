import os
import subprocess
import tempfile
import coverage
from pylint.lint import Run
from pylint.reporters import JSONReporter
from io import StringIO
import sys
from typing import Tuple, Dict

class PostProcessValidator:
    def __init__(self, helpers=None):
        self.helpers = helpers  # Optional, for centralized logging or notifications

    def run_test_coverage(self, file_path: str) -> Tuple[bool, float, str]:
        """Run coverage on the target file, return (success, coverage_percent, output_log)."""
        cov = coverage.Coverage(source=[os.path.dirname(file_path)])
        cov.start()

        module_name = os.path.splitext(os.path.basename(file_path))[0]

        try:
            # Dynamically import & test the file (assumes tests exist in the same dir or nearby)
            exec(f"import {module_name}")
            success = True
        except Exception as e:
            cov.stop()
            cov.save()
            return False, 0.0, f"Failed to run tests: {e}"

        cov.stop()
        cov.save()

        try:
            coverage_percent = cov.report(show_missing=True)
            output_log = f"✅ Test coverage: {coverage_percent:.2f}%"
            success = True
        except coverage.CoverageException as e:
            output_log = f"❌ Coverage report failed: {e}"
            success = False
            coverage_percent = 0.0

        return success, coverage_percent, output_log

    def run_pylint(self, file_path: str) -> Tuple[bool, float, str]:
        """Run pylint and return (success, score, output_log)."""
        output_stream = StringIO()
        reporter = JSONReporter(output_stream)
        
        # Capture the original stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            Run([file_path, '--output-format=json'], reporter=reporter, exit=False)
            pylint_output = sys.stdout.getvalue()
        finally:
            # Restore stdout
            sys.stdout = old_stdout
        
        score = self.extract_pylint_score(pylint_output)
        success = score >= 8.0  # Arbitrary pass threshold

        return success, score, pylint_output

    def extract_pylint_score(self, pylint_output: str) -> float:
        """Extract the score from pylint output."""
        for line in pylint_output.splitlines():
            if "Your code has been rated at" in line:
                try:
                    score_str = line.split("rated at")[1].split("/")[0].strip()
                    return float(score_str)
                except (IndexError, ValueError):
                    continue
        return 0.0

    def run_mypy(self, file_path: str) -> Tuple[bool, str]:
        """Run mypy and return (success, output_log)."""
        result = subprocess.run(['mypy', file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        success = result.returncode == 0
        output = result.stdout + "\n" + result.stderr

        return success, output

    def run_black_check(self, file_path: str) -> Tuple[bool, str]:
        """Run black in check mode (format validation only)."""
        result = subprocess.run(['black', '--check', file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        success = result.returncode == 0
        output = result.stdout + "\n" + result.stderr

        return success, output

    def run_full_validation(self, file_path: str) -> Dict:
        """Run all checks on the given file and return detailed report."""
        report = {}

        # ✅ Run Test Coverage
        test_success, test_coverage, test_log = self.run_test_coverage(file_path)
        report['test_coverage'] = {
            'success': test_success,
            'coverage_percent': test_coverage,
            'log': test_log
        }

        # ✅ Run pylint
        pylint_success, pylint_score, pylint_log = self.run_pylint(file_path)
        report['pylint'] = {
            'success': pylint_success,
            'score': pylint_score,
            'log': pylint_log
        }

        # ✅ Run mypy
        mypy_success, mypy_log = self.run_mypy(file_path)
        report['mypy'] = {
            'success': mypy_success,
            'log': mypy_log
        }

        # ✅ Run black
        black_success, black_log = self.run_black_check(file_path)
        report['black'] = {
            'success': black_success,
            'log': black_log
        }

        # ✅ Summary Output (Optional Helper Message)
        summary_msg = (
            f"📄 Validation Report for {os.path.basename(file_path)}\n"
            f"------------------------------\n"
            f"✅ Test Coverage: {test_coverage:.2f}%\n"
            f"✅ Pylint Score: {pylint_score:.2f}/10\n"
            f"✅ Mypy: {'PASS' if mypy_success else 'FAIL'}\n"
            f"✅ Black Format: {'PASS' if black_success else 'FAIL'}\n"
        )

        if self.helpers:
            self.helpers.log(summary_msg)

        return report

# Example CLI Run (for debug purposes)
if __name__ == "__main__":
    validator = PostProcessValidator()
    file_to_check = "path_to_your_python_file.py"  # Replace with your file path
    results = validator.run_full_validation(file_to_check)

    # Simple printout
    from pprint import pprint
    pprint(results)
